"""Small server-rendered interface with real authenticated forms and CSRF checks."""

import hmac
from io import BytesIO
from pathlib import Path
import secrets

from flask import Flask, request, session, redirect, url_for, render_template, send_file, flash, jsonify
from app.service import BusinessError


TEXT = {
    "Team files":"团队文件", "My files":"我的文件", "Shared with me":"收到的文件", "Review queue":"待审核", "Messages":"消息中心", "Sign out":"退出登录", "Sign in":"登录", "Username":"账号", "Password":"密码", "Upload file":"上传文件", "Choose a file":"选择文件", "Share":"申请共享", "Recipient":"接收成员", "Reviewer":"审核人", "Download":"下载", "File":"文件", "Size":"大小", "Owner":"文件主人", "Status":"状态", "Actions":"操作", "Approve":"通过", "Reject":"驳回", "Cancel":"取消申请", "Revoke":"撤销共享", "Mark read":"标为已读", "Read":"已读", "New":"未读", "No files yet":"暂无文件。上传文件后可选择成员和审核人。", "No shared files":"暂无已获授权的文件。审核通过后会显示在这里。", "Nothing to review":"暂无等待你审核的共享申请。", "No messages":"暂无站内消息。", "Sharing history":"共享记录", "Share file":"共享文件", "Apply for sharing":"提交共享申请", "Business graph":"业务图", "Review result":"审核结果", "Sharing notification":"共享通知", "Selected reviewer":"指定审核人", "Trial accounts":"本地试用账号", "Trial password":"测试密码", "Access is checked each time you download.":"每次下载都会检查当前权限。", "Files stay private until the selected reviewer approves sharing.":"文件上传后保持私有，共享经指定审核人通过后生效。", "Language":"语言", "Save":"切换", "pending":"待审核", "approved":"已通过", "rejected":"已驳回", "cancelled":"已取消", "revoked":"已撤销", "invalid_login":"账号或密码不正确。", "permission_denied":"当前没有执行此操作的权限。", "not_found":"记录不存在。", "recipient_must_differ":"请选择另一位成员作为接收方。", "share_already_active":"该文件与成员之间已有待审核或已通过的共享。", "invalid_transition":"该申请当前不能执行此操作。", "invalid_filename":"请使用有效的文件名。", "file_too_large":"文件超过 20 MB，请选择较小的文件。", "csrf_failed":"页面凭据已失效，请刷新后重试。", "invalid_action":"无法识别该操作。", "saved":"操作已保存。", "file_required":"请先选择文件。", "Select":"请选择"
}


def create_app(service, graph_url="", build_id="unbound"):
    root=Path(__file__).resolve().parents[1]
    app=Flask(__name__,template_folder=str(root/"templates"),static_folder=str(root/"static"),static_url_path="/static")
    secret_path=service.store.directory/"session-secret"
    if not secret_path.exists():
        secret_path.write_bytes(secrets.token_bytes(32))
    app.secret_key=secret_path.read_bytes()
    app.config.update(MAX_CONTENT_LENGTH=21*1024*1024,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE="Lax")

    @app.context_processor
    def context():
        locale=session.get("locale","zh-CN")
        return {"t":lambda text:TEXT.get(text,text) if locale=="zh-CN" else text,"locale":locale,"csrf":session.setdefault("csrf",secrets.token_urlsafe(24)),"graph_url":graph_url,"user":session.get("user")}

    @app.route("/",methods=["GET","POST"])
    def page():
        if request.method=="POST":
            action=request.form.get("action","")
            with service.monitor.span("http_action",lambda:{"inputs":{"action":action}}) as operation:
                try:
                    if not hmac.compare_digest(request.form.get("csrf",""),session.get("csrf","missing")):
                        raise BusinessError("csrf_failed",400)
                    actor_id=session.get("user",{}).get("id","")
                    if action=="login":
                        user=service.login(request.form.get("username",""),request.form.get("password",""))
                        locale=session.get("locale","zh-CN")
                        session.clear()
                        session.update(user=user,locale=locale,csrf=secrets.token_urlsafe(24))
                    elif action=="language":
                        session["locale"]="en" if request.form.get("locale")=="en" else "zh-CN"
                    elif not actor_id:
                        raise BusinessError("permission_denied",401)
                    elif action=="logout":
                        service.logout(actor_id)
                        locale=session.get("locale","zh-CN")
                        session.clear()
                        session["locale"]=locale
                    elif action=="upload":
                        file=request.files.get("file")
                        if file is None or not file.filename:
                            raise BusinessError("file_required",400)
                        service.upload(actor_id,file.filename,file.read())
                        flash("saved","success")
                    elif action=="share":
                        service.request_share(actor_id,request.form.get("file_id",""),request.form.get("recipient_id",""),request.form.get("reviewer_id",""))
                        flash("saved","success")
                    elif action in {"approve","reject","cancel","revoke"}:
                        service.change_share(actor_id,request.form.get("share_id",""),action)
                        flash("saved","success")
                    elif action=="read_notification":
                        service.read_notification(actor_id,request.form.get("notification_id",""))
                    else:
                        raise BusinessError("invalid_action",400)
                    operation.result(lambda:{"outputs":{"status":303}})
                except BusinessError as error:
                    operation.result(lambda:{"outputs":{"status":error.status}})
                    flash(error.code,"error")
                    return redirect(url_for("page"),303)
            return redirect(url_for("page"),303)
        if "user" not in session:
            return render_template("login.html")
        with service.monitor.span("http_page",lambda:{"inputs":{"actor_id":session["user"]["id"]}}) as operation:
            data=service.dashboard(session["user"]["id"])
            operation.result(lambda:{"outputs":{"status":200}})
            return render_template("workspace.html",data=data,names={item["id"]:item["name"] for item in data["members"]})

    @app.get("/download/<file_id>")
    def download(file_id):
        with service.monitor.span("http_download",lambda:{"inputs":{"file_id":file_id}}) as operation:
            try:
                filename,content=service.download(session.get("user",{}).get("id",""),file_id)
                response=send_file(BytesIO(content),as_attachment=True,download_name=filename,mimetype="application/octet-stream")
                response.headers["Cache-Control"]="no-store, private"
                response.headers["X-Content-Type-Options"]="nosniff"
                operation.result(lambda:{"outputs":{"status":200}})
                return response
            except BusinessError as error:
                operation.result(lambda:{"outputs":{"status":error.status}})
                return render_template("error.html",error=error.code),error.status

    @app.get("/api/bo/health")
    def health():
        return jsonify(status="ready",build_id=build_id,application="team-file-sharing-lifecycle")

    @app.errorhandler(413)
    def too_large(error):
        return render_template("error.html",error="file_too_large"),413

    return app
