"""Run accepted concept-model browser regressions with an isolated real application.

Replay byte-verified synthetic dialogue source through the ordinary acceptance
workflow, start the resulting application and observer on ephemeral ports, then
exercise maintained assets with Playwright. This is a repeatable CI fixture, not
a new user study. The historical source and acceptance evidence remain unchanged.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import uuid

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/vibelens"
TRIAL = ROOT / "docs/review/concept-models-20261104/trial"


def run_browser(project, evidence):
    """Serve actual accepted state and preserve browser/capture failures as evidence."""
    sys.path[:0] = [str(project), str(SKILL / "scripts")]
    os.environ["BO_TRIAL_DATABASE_URL"] = "sqlite:///var/files.sqlite3"
    from app import create_app
    from service import FileService
    from bo_integration import BOIntegration
    from bo_observer.service import GraphSession, make_server as graph_server
    from werkzeug.serving import make_server as app_server

    session = GraphSession(project)
    files = FileService(project / "var")
    integration = BOIntegration(project, session, files)
    app = create_app(files)
    integration.bo_bind_flask(app)
    application = app_server("127.0.0.1", 0, app, threaded=True)
    application_url = f"http://127.0.0.1:{application.server_port}"
    viewer = graph_server(session, 0, origins=[application_url])
    graph_url = f"http://127.0.0.1:{viewer.server_port}/graph?lang=zh-CN"
    threads = [
        threading.Thread(target=server.serve_forever, daemon=True)
        for server in (application, viewer)
    ]
    for thread in threads:
        thread.start()
    try:
        result = subprocess.run(
            [
                "node",
                str(
                    ROOT
                    / "tools"
                    / os.environ.get("BO_CONCEPT_BROWSER_SCRIPT", "test_concept_browser.mjs")
                ),
            ],
            cwd=ROOT,
            env={
                **os.environ,
                "BO_CONCEPT_URL": graph_url,
                "BO_CONCEPT_APP_URL": application_url,
                "BO_CONCEPT_EVIDENCE": str(evidence),
                # This fixture shares business/native IDs, but its conceptual
                # state event binds to the native share call under a distinct ID.
                "BO_CONCEPT_CAPTURE_ID": "event:grant:share",
            },
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
        )
        (evidence / "browser.stdout").write_text(result.stdout, encoding="utf-8")
        (evidence / "browser.stderr").write_text(result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(f"Concept browser check failed; inspect {evidence}")
        return json.loads(result.stdout.strip().splitlines()[-1])
    finally:
        for server in (application, viewer):
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=5)
        integration.close()


def main():
    """Give every run fresh source, database, recording and preference directories."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(os.environ.get("BO_CONCEPT_EVIDENCE", ROOT / ".validation/concept-browser")),
    )
    options = parser.parse_args()
    run = options.out.resolve() / ("run-" + uuid.uuid4().hex[:12])
    run.mkdir(parents=True)
    project = run / "project"
    environment = {**os.environ, "VIBELENS_SKILL": str(SKILL)}
    accepted = subprocess.run(
        [
            sys.executable,
            "-B",
            "-X",
            "utf8",
            str(TRIAL / "replay.py"),
            "--skill",
            str(SKILL),
            "--out",
            str(project),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=720,
    )
    (run / "acceptance.stdout").write_text(accepted.stdout, encoding="utf-8")
    (run / "acceptance.stderr").write_text(accepted.stderr, encoding="utf-8")
    if accepted.returncode:
        raise RuntimeError(f"Concept fixture acceptance failed; inspect {run}")
    result = run_browser(project, run)
    print(json.dumps({**result, "evidence": str(run)}))


if __name__ == "__main__":
    main()
