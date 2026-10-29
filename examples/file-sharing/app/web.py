"""Server-rendered HTTP interface with session and request-bound authorization."""

import io
from pathlib import Path
import secrets
from flask import (Blueprint, Flask, current_app, request, session, redirect,
                   url_for, render_template, send_file, jsonify, flash)
from .service import SharingService, DomainError
from .storage import Store, DEMO_USERS

pages = Blueprint("pages", __name__)


def service():
    return current_app.extensions["sharing"]


def current_actor():
    return session.get("user_id", "")


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]


@pages.before_request
def check_csrf():
    if request.method == "POST":
        supplied = request.form.get("csrf", "")
        if not supplied or not secrets.compare_digest(supplied, session.get("csrf", "")):
            raise DomainError("csrf_invalid", 400)


@pages.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = service().authenticate(request.form.get("username", ""), request.form.get("password", ""))
        session.clear()
        session["user_id"] = user["id"]
        csrf_token()
        return redirect(url_for("pages.dashboard"))
    return render_template("login.html", demo_users=DEMO_USERS)


@pages.get("/")
def dashboard():
    actor = current_actor()
    if not actor:
        return redirect(url_for("pages.login"))
    user = service().store.user(actor)
    if not user:
        session.clear()
        return redirect(url_for("pages.login"))
    items = service().list_files(actor)
    recipients = [user for user in service().list_users(actor) if user["id"] != actor]
    return render_template("dashboard.html", user=user,
        owned=[item for item in items if item["is_owner"]],
        received=[item for item in items if not item["is_owner"]], users=recipients,
        graph_url=current_app.config.get("GRAPH_URL"))


@pages.post("/upload")
def upload():
    upload_file = request.files.get("file")
    if upload_file is None:
        raise DomainError("file_required", 400)
    service().upload(current_actor(), upload_file.filename or "", upload_file.read(16 * 1024 * 1024 + 1))
    flash("文件已上传。你是这个文件的所有者。")
    return redirect(url_for("pages.dashboard"))


@pages.post("/files/<file_id>/share")
def share(file_id: str):
    service().share(current_actor(), file_id, request.form.get("recipient_id", ""))
    flash("共享成功。接收者现在可以查看文件信息和下载。")
    return redirect(url_for("pages.dashboard"))


@pages.get("/files/<file_id>/download")
def download(file_id: str):
    filename, content = service().download(current_actor(), file_id)
    return send_file(io.BytesIO(content), mimetype="application/octet-stream", as_attachment=True,
                     download_name=filename, max_age=0)


@pages.post("/files/<file_id>/revoke")
def revoke(file_id: str):
    service().revoke(current_actor(), file_id, request.form.get("recipient_id", ""))
    flash("共享已取消。该接收者不能再下载此文件，你仍可查看和下载。")
    return redirect(url_for("pages.dashboard"))


@pages.post("/logout")
def logout():
    service().logout(current_actor())
    session.clear()
    return redirect(url_for("pages.login"))


@pages.get("/api/files")
def list_files():
    return jsonify(service().list_files(current_actor()))


def handle_error(error):
    messages = {"invalid_credentials": "账号或密码不正确。", "permission_denied": "你没有操作这个文件的权限。",
        "login_required": "请先登录。", "file_not_found": "文件不存在。", "recipient_not_found": "接收者不存在。",
        "invalid_filename": "文件名无效或过长。", "file_too_large": "文件不能超过 16 MB。",
        "csrf_invalid": "页面凭证已过期，请返回登录页重新操作。", "file_required": "请先选择文件。"}
    if request.path.startswith("/api/"):
        return jsonify(error=error.code), error.status
    return render_template("error.html", message=messages.get(error.code, "操作未完成。"), status=error.status), error.status


def secure_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
    return response


def create_app(root=None, database=None, bo_trace=None, bo_data=None, graph_url=None):
    root = Path(root or Path(__file__).resolve().parents[1])
    app = Flask(__name__, template_folder=str(root / "templates"), static_folder=str(root / "static"))
    data_path = root / "data"
    data_path.mkdir(exist_ok=True)
    secret_path = data_path / "session.key"
    if not secret_path.exists():
        try:
            with secret_path.open("x", encoding="ascii") as secret_file:
                secret_file.write(secrets.token_hex(32))
        except FileExistsError:
            pass
    app.config.update(SECRET_KEY=secret_path.read_text(encoding="ascii"), MAX_CONTENT_LENGTH=17 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", TRUSTED_HOSTS=["localhost", "127.0.0.1"], GRAPH_URL=graph_url)
    store = Store(Path(database or data_path / "sharing.sqlite3"), bo_data)
    store.initialize()
    app.extensions["sharing"] = SharingService(root, store, bo_trace)
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.register_blueprint(pages)
    app.register_error_handler(DomainError, handle_error)
    app.after_request(secure_headers)
    return app
