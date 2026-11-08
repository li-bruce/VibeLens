"""Local file-sharing HTTP application with explicit test-user selection."""

from pathlib import Path
from flask import Flask, Response, jsonify, request
from service import AccessDenied, FileService


def create_app(service=None):
    """Construct the real Flask routes; callers may attach external observation."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    files = service or FileService(Path(__file__).parent / "var")

    def actor():
        """Resolve an explicitly selected local test identity."""
        value = request.headers.get("X-User", request.args.get("user", "Alice"))
        if value not in {"Alice", "Bob", "Carol"}:
            raise ValueError("Unknown test user")
        return value

    @app.get("/")
    def home():
        """Display upload, sharing and received-file controls."""
        return Path(__file__).with_name("index.html").read_text(encoding="utf-8")

    @app.post("/api/files")
    def upload():
        """Upload one file for the current test user."""
        item = request.files["file"]
        return jsonify(files.upload(actor(), item.filename, item.read())), 201

    @app.post("/api/files/<file_id>/share")
    def share(file_id: str):
        """Share the named file with the colleague supplied in the request."""
        return jsonify(files.share(actor(), file_id, request.json["recipient"]))

    @app.post("/api/files/<file_id>/revoke")
    def revoke(file_id: str):
        """Revoke the selected colleague's access to the named file."""
        return jsonify(files.revoke(actor(), file_id, request.json["recipient"]))

    @app.get("/api/received")
    def received():
        """List files currently shared with the selected colleague."""
        return jsonify(files.received(actor()))

    @app.get("/api/files/<file_id>/download")
    def download(file_id: str):
        """Return stored bytes only after the current recipient grant passes."""
        return Response(files.download(actor(), file_id), mimetype="application/octet-stream")

    @app.errorhandler(AccessDenied)
    def denied(error):
        """Preserve the real permission-denied HTTP status."""
        return jsonify(error=str(error)), 403

    @app.errorhandler(FileNotFoundError)
    def missing(error):
        """Return a missing-resource response for an unknown file identity."""
        return jsonify(error="File not found"), 404

    return app


if __name__ == "__main__":
    create_app().run(port=8917)
