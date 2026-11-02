"""Local HTTP entrypoints; every business request retains its real exit status."""
import io
from pathlib import Path
import secrets
from flask import Flask, request, session, g, redirect, url_for, render_template, jsonify, send_file
from .service import FileService, DomainError
from .storage import Store
from .ports import NullProbe

class WebRoutes:
    def __init__(self, app, service, probe):
        self.app, self.service, self.bo_probe = app, service, probe

    def before_request(self):
        g.bo_http = self.bo_probe.span("http_request", lambda: {"inputs": {
            "method": request.method, "path": request.path}})
        g.bo_http_activation = g.bo_http.__enter__()
        if request.method == "POST":
            expected = session.get("csrf_token", "")
            supplied = request.form.get("csrf_token", "")
            if not expected or not supplied or not secrets.compare_digest(supplied, expected):
                raise DomainError("csrf_denied", 400)

    def after_request(self, response):
        if getattr(g, "bo_http", None):
            g.bo_http_activation.result(lambda: {"outputs": {"status": response.status_code}})
            g.bo_http.__exit__(None, None, None)
            g.bo_http = None
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'"
        return response

    def teardown_request(self, error):
        if getattr(g, "bo_http", None):
            g.bo_http.__exit__(type(error), error, error.__traceback__) if error else g.bo_http.__exit__(None, None, None)
            g.bo_http = None

    def actor(self):
        identifier = session.get("user_id", "")
        if not identifier:
            raise DomainError("login_required", 401)
        return identifier

    def index(self):
        session.setdefault("csrf_token", secrets.token_urlsafe(24))
        if not session.get("user_id"):
            return render_template("login.html")
        actor = self.actor()
        return render_template("index.html", actor=actor, accounts=self.service.users(),
            files=self.service.visible_files(actor))

    def login(self):
        username = request.form.get("username", "")
        if not self.service.login(username, request.form.get("password", "")):
            raise DomainError("invalid_credentials", 401)
        session.clear()
        session.update(user_id=username, csrf_token=secrets.token_urlsafe(24))
        return redirect(url_for("index"))

    def logout(self):
        with self.bo_probe.span("sign_out", lambda: {"inputs": {"actor": session.get("user_id", "")}}) as activation:
            session.clear()
            activation.result(lambda: {"outputs": {"logged_out": True}})
        return redirect(url_for("index"))

    def upload(self):
        actor = self.actor()
        incoming = request.files.get("file")
        if not incoming or not incoming.filename:
            raise DomainError("file_required", 400)
        filename = incoming.filename.replace("\\", "/").rsplit("/", 1)[-1]
        row = self.service.upload(actor, request.form.get("reviewer_id", ""), filename,
            incoming.stream.read(10 * 1024 * 1024 + 1))
        if request.accept_mimetypes.best == "application/json":
            return jsonify(row), 201
        return redirect(url_for("index"))

    def review(self, file_id):
        row = self.service.review(self.actor(), file_id, request.form.get("decision", ""), request.form.get("reason", ""))
        return jsonify(row) if request.accept_mimetypes.best == "application/json" else redirect(url_for("index"))

    def share(self, file_id):
        row = self.service.share(self.actor(), file_id, request.form.get("recipient_id", ""))
        return jsonify(row) if request.accept_mimetypes.best == "application/json" else redirect(url_for("index"))

    def withdraw(self, file_id):
        row = self.service.withdraw(self.actor(), file_id)
        return jsonify(row) if request.accept_mimetypes.best == "application/json" else redirect(url_for("index"))

    def file_info(self, file_id):
        actor = self.actor()
        row = self.service.access(actor, file_id)
        if request.args.get("view") == "details" or request.accept_mimetypes.best == "text/html":
            return render_template("details.html", actor=actor, file=row)
        return jsonify(row)

    def download(self, file_id):
        row = self.service.access(self.actor(), file_id, True)
        return send_file(io.BytesIO(row["content"]), as_attachment=True, download_name=row["filename"],
            mimetype="application/octet-stream", max_age=0)

    def error(self, error):
        messages = {"login_required": "请先登录。", "invalid_credentials": "账号或密码不正确。",
            "upload_denied": "请选择一位已有的其他同事审核。", "review_denied": "只有本次指定的审核人可以审核。",
            "share_denied": "只有上传者可以在审核通过后分享。", "access_denied": "你没有这个文件的访问权限。",
            "review_closed": "这份文件的审核已经结束。", "csrf_denied": "页面已过期，请刷新后再提交。",
            "withdraw_denied": "只有上传者可以撤回仍待审核的文件。",
            "rejection_reason_required": "不通过审核时，请填写拒绝原因。",
            "recipient_already_set": "这份文件已经指定接收人。"}
        if request.accept_mimetypes.best == "application/json":
            return jsonify(error=error.code), error.status
        return render_template("error.html", message=messages.get(error.code, "操作未完成，请检查输入。")), error.status

def create_app(root: Path, database=None, bo_probe=None, bo_observer=None, bo_data=None):
    probe = bo_probe or NullProbe()
    app = Flask(__name__, template_folder=str(root / "templates"), static_folder=str(root / "static/app"))
    app.config.update(MAX_CONTENT_LENGTH=11 * 1024 * 1024, SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict")
    secret_path = root / "var/session-secret"
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    if not secret_path.exists():
        secret_path.write_bytes(secrets.token_bytes(32))
    app.secret_key = secret_path.read_bytes()
    store = Store(database or root / "var/team-files.sqlite3", bo_data)
    store.initialize()
    service = FileService(root, store, probe, bo_observer)
    routes = WebRoutes(app, service, probe)
    app.before_request(routes.before_request)
    app.after_request(routes.after_request)
    app.teardown_request(routes.teardown_request)
    app.register_error_handler(DomainError, routes.error)
    app.add_url_rule("/", "index", routes.index)
    app.add_url_rule("/login", "login", routes.login, methods=["POST"])
    app.add_url_rule("/logout", "logout", routes.logout, methods=["POST"])
    app.add_url_rule("/upload", "upload", routes.upload, methods=["POST"])
    app.add_url_rule("/files/<file_id>/review", "review", routes.review, methods=["POST"])
    app.add_url_rule("/files/<file_id>/share", "share", routes.share, methods=["POST"])
    app.add_url_rule("/files/<file_id>/withdraw", "withdraw", routes.withdraw, methods=["POST"])
    app.add_url_rule("/files/<file_id>", "file_info", routes.file_info)
    app.add_url_rule("/files/<file_id>/download", "download", routes.download)
    app.extensions.update(trial_store=store, trial_service=service)
    return app
