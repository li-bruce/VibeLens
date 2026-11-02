"""Small server-rendered UI and JSON API sharing the same native entrypoint."""
import io
import secrets
from contextlib import nullcontext
from flask import Flask, current_app, request, session, jsonify, render_template, redirect, url_for, send_file
from app.service import BusinessError


LABELS = {
    "zh-CN": {"title": "团队文件", "files": "文件", "review": "审核", "messages": "消息", "login": "登录", "logout": "退出", "upload": "上传文件", "name": "文件名", "owner": "上传者", "status": "审核结果", "download": "下载", "share": "分享", "approve": "通过", "reject": "驳回", "reason": "驳回原因", "empty": "这里还没有记录。", "username": "账号", "password": "密码", "recipient": "指定同事", "graph": "查看 VibeLens", "refresh": "刷新", "pending": "待审核", "approved": "已通过", "rejected": "已驳回", "admin": "管理员", "member": "成员", "notice": "消息由后台稍后送达；分享成功后立即可下载。", "trial": "试用账号：admin1、admin2、member1、member2；统一密码 Trial-2026!", "success": "操作完成", "login_failed": "账号或密码不正确。"},
    "en": {"title": "Team files", "files": "Files", "review": "Review", "messages": "Messages", "login": "Sign in", "logout": "Sign out", "upload": "Upload file", "name": "Filename", "owner": "Uploader", "status": "Review outcome", "download": "Download", "share": "Share", "approve": "Approve", "reject": "Reject", "reason": "Rejection reason", "empty": "No records yet.", "username": "Account", "password": "Password", "recipient": "Colleague", "graph": "Open VibeLens", "refresh": "Refresh", "pending": "Pending", "approved": "Approved", "rejected": "Rejected", "admin": "Administrator", "member": "Member", "notice": "Notices arrive later. A successful share grants immediate download access.", "trial": "Trial accounts: admin1, admin2, member1, member2. Password: Trial-2026!", "success": "Done", "login_failed": "Incorrect account or password."},
}


def create_app(service, secret, graph_url=""):
    app = Flask(__name__, template_folder="templates", static_folder="static/app", static_url_path="/static")
    app.secret_key = secret
    app.url_map.redirect_defaults = False
    app.config.update(SERVICE=service, GRAPH_URL=graph_url, MAX_CONTENT_LENGTH=11 * 1024 * 1024, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict")
    app.add_url_rule("/", defaults={"operation": "files"}, view_func=api_entry, methods=["GET"])
    app.add_url_rule("/<operation>", view_func=api_entry, methods=["GET", "POST"])
    app.add_url_rule("/api/<operation>", view_func=api_entry, methods=["GET", "POST"])
    app.add_url_rule("/api/stategraph/export", view_func=bo_stategraph_query, methods=["GET"])
    return app


def bo_stategraph_query():
    from bo_stategraph import BOStateGraph
    from bo_stategraph.query import machine_snapshot
    from behavior_model import capture
    service = current_app.config["SERVICE"]
    document = __import__("json").loads((service.root / "bo_stategraph/project.json").read_text(encoding="utf-8"))
    manifest = capture(service.root, document["model"])
    graph = BOStateGraph(document["model"], build_id=manifest["build_id"], mode="drive")
    return jsonify(graph.bo_export(runtime={"machine": machine_snapshot(service.store, manifest["build_id"])}))


def api_entry(operation):
    service = current_app.config["SERVICE"]
    bo_http = getattr(service.bo, "http", None)
    with bo_http(operation) if bo_http else nullcontext() as boundary:
        try:
            response = dispatch(service, operation)
            code = response[1] if isinstance(response, tuple) else getattr(response, "status_code", 200)
        except BusinessError as error:
            code = error.status
            response = (jsonify({"ok": False, "code": error.code}), code) if request.path.startswith("/api/") else (render_page(service, operation, error=error.code), code)
        if boundary:
            boundary.set_attribute("http.response.status_code", code)
        return response


def render_page(service, operation, *, error="", rows=None):
    locale = request.args.get("lang", session.get("locale", "zh-CN"))
    locale = locale if locale in LABELS else "en"
    session["locale"] = locale
    session.setdefault("csrf", secrets.token_urlsafe(24))
    actor = service.user(session.get("user_id", ""))
    page = operation if operation in ("files", "review", "messages") else "files"
    return render_template("index.html", labels=LABELS[locale], locale=locale, actor=actor, page=page, rows=rows or [], error=error, csrf=session["csrf"], graph_url=current_app.config["GRAPH_URL"], notice=request.args.get("done"), accounts=["admin1", "admin2", "member1", "member2"])


def dispatch(service, operation):
    actor = service.user(session.get("user_id", ""))
    api = request.path.startswith("/api/")
    body = (request.get_json(silent=True) or {}) if request.is_json else request.form
    if operation == "session":
        session.setdefault("csrf", secrets.token_urlsafe(24))
        return jsonify({"actor": actor, "csrf": session["csrf"]})
    if request.method == "POST":
        if request.headers.get("Origin") not in (None, request.host_url.rstrip("/")):
            raise BusinessError("origin_denied")
        token = body.get("csrf", request.headers.get("X-CSRF-Token", ""))
        if not session.get("csrf") or not secrets.compare_digest(str(token), session["csrf"]):
            raise BusinessError("csrf_denied")
        if operation == "login":
            user = service.sign_in(str(body.get("username", "")), str(body.get("password", "")))
            if not user:
                return (jsonify({"ok": False, "code": "login_failed"}), 401) if api else (render_page(service, "files", error="login_failed"), 401)
            session.clear()
            session.update(user_id=user["id"], csrf=secrets.token_urlsafe(24))
            result = {"ok": True, "actor": user}
        elif operation == "logout":
            service.sign_out(actor, session.clear)
            result = {"ok": True}
        elif operation == "upload":
            incoming = request.files.get("file")
            if incoming is None:
                raise BusinessError("file_required", 400)
            result = service.upload_file(actor, incoming.filename or "", incoming.read(10 * 1024 * 1024 + 1))
        elif operation == "review":
            result = service.review_file(actor, str(body.get("file_id", "")), str(body.get("verdict", "")), str(body.get("reason", "")))
            if result.get("ok") is False:
                raise BusinessError(result["code"], result["status"])
        elif operation == "share":
            recipients = body.get("recipient_ids", []) if request.is_json else request.form.getlist("recipient_id")
            if not isinstance(recipients, list) or any(not isinstance(value, str) for value in recipients):
                raise BusinessError("invalid_recipients", 400)
            result = service.share_file(actor, str(body.get("file_id", "")), recipients)
        else:
            raise BusinessError("operation_not_found", 404)
        return jsonify(result) if api else redirect(url_for("api_entry", operation="review" if operation == "review" else "files", done="1"))
    if operation == "download":
        file = service.access_file(actor, request.args.get("file_id", ""))
        return send_file(io.BytesIO(file["content"]), as_attachment=True, download_name=file["name"], mimetype="application/octet-stream")
    if operation not in ("files", "review", "messages"):
        raise BusinessError("operation_not_found", 404)
    if not actor:
        return (jsonify({"code": "sign_in_required"}), 401) if api else render_page(service, operation)
    rows = service.list_messages(actor) if operation == "messages" else service.list_files(actor, review=operation == "review")
    return jsonify({"items": rows}) if api else render_page(service, operation, rows=rows)
