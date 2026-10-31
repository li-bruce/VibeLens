"""Review managed runtime updates while keeping existing example gates intact."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CHANGE = os.environ.get("BO_DIALOGUE_EXAMPLE_CHANGE", ".stategraph/dialogue-capture-20261031")
OUT = ROOT / "docs/review/dialogue-acceptance-20261031"
REQUEST = os.environ.get("BO_DIALOGUE_REQUEST", "Reduce repeated declaration parsing measured during independent dialogue acceptance. Keep current source-byte reads, physical containment, canonical JSON identity, capture boundaries and application behavior.")
MANAGED_REASON = os.environ.get("BO_DIALOGUE_REASON")
HTTP_UPDATE = os.environ.get("BO_DIALOGUE_EXAMPLE_HTTP") == "1"
os.environ["BO_ADAPTER_HOME"] = str(ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript")


def run(root, *arguments):
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", *map(str, arguments)],
                            cwd=root, capture_output=True, text=True, encoding="utf-8")
    if len(arguments) > 1 and arguments[1] == "inspect":
        value = json.loads(result.stdout)
        if value.get("candidate_id"):
            return value  # Missing review is expected before writing this candidate's review.
    if result.returncode:
        print(result.stdout[-12000:], result.stderr[-1500:])
        raise SystemExit(result.returncode)
    try:
        return json.loads(result.stdout)
    except ValueError:
        return {"stdout": result.stdout}


receipts = []
for name, runtime in [("delivery", "observer_generated/runtime"), ("team-archive", "observer_runtime")]:
    root = ROOT / "examples" / name
    cli = root / runtime / "change_sync.py"
    cfg = json.loads((root / "sync.json").read_text(encoding="utf-8"))
    diff = subprocess.check_output(["git", "diff", "HEAD", "--", *[str(root / p) for p in cfg["code_files"]]],
                                   cwd=ROOT, text=True)
    reviewed_http = False
    if HTTP_UPDATE:
        relative = (root / "integrations/bo_server.py").relative_to(ROOT).as_posix()
        before = subprocess.check_output(["git", "show", "HEAD:" + relative], cwd=ROOT, text=True)
        replacements = [
            ("from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer", "from http.server import BaseHTTPRequestHandler"),
        ]
        if name == "delivery":
            replacements += [
                ("from observer_generated.runtime.bo_web import BOWeb", "from observer_generated.runtime.bo_web import BOWeb, BOHTTPServer"),
                ('server = ThreadingHTTPServer(("127.0.0.1", port), Handler)', 'server = BOHTTPServer(("127.0.0.1", port), Handler)'),
            ]
        else:
            replacements += [
                ("from observer_runtime.bo_web import BOWeb", "from observer_runtime.bo_web import BOWeb, BOHTTPServer, bo_content_type"),
                ('return self.reply(200,raw,(mimetypes.guess_type(path.name)[0] or "application/octet-stream")+"; charset=utf-8")',
                 'return self.reply(200,raw,bo_content_type(mimetypes.guess_type(path.name)[0] or "application/octet-stream"))'),
                ('server=ThreadingHTTPServer(("127.0.0.1",args.port),Handler)', 'server=BOHTTPServer(("127.0.0.1",args.port),Handler)'),
            ]
        expected = before
        for old, new in replacements:
            if expected.count(old) != 1:
                raise SystemExit("The exact reviewed HTTP-only patch no longer applies: " + name)
            expected = expected.replace(old, new, 1)
        if (root / "integrations/bo_server.py").read_text(encoding="utf-8") != expected:
            raise SystemExit("Unreviewed integration change outside the exact HTTP-only patch: " + name)
        changed = subprocess.check_output(["git", "diff", "--name-only", "HEAD", "--", *[str(root / p) for p in cfg["code_files"]]], cwd=ROOT, text=True).splitlines()
        if set(changed) - {relative}:
            raise SystemExit("Unreviewed native business drift: " + repr(changed))
        reviewed_http = True
    if diff.strip() and not reviewed_http:
        raise SystemExit("Business source drift must be reviewed separately: " + name)
    if sys.argv[1] == "begin":
        run(root, cli, "check", "--root", ".")
        value = run(root, cli, "begin", "--root", ".", "--change", CHANGE, "--request",
                    REQUEST)
        receipts.append({"project": name, "begin": value})
        continue
    previous = Path(json.loads((root / ".release/stategraph/active.json").read_text())["change"]).name
    review = json.loads((root / ".release/stategraph" / previous / "review.json").read_text(encoding="utf-8"))
    reason = "Reviewed managed observer update: skip repeated declaration parsing only for byte-identical previously verified JSON. Fresh bytes, same-stat edits, physical containment and canonical comparison remain checked. Business source and protected scenarios remain unchanged."
    reason = MANAGED_REASON or reason
    if name == "delivery":
        run(root, "tooling/dev.py", "graph", "--reason", reason)
    else:
        run(root, "tooling/build_model.py")
        run(root, runtime + "/architecture_guard.py", "seal", "--root", ".", "--reason", reason)
    impact = run(root, cli, "inspect", "--root", ".")
    review["candidate_id"] = impact["candidate_id"]
    review["decisions"]["business"] = {"action": "unchanged", "reason": "Git confirms byte-identical configured code_files; all protected requirements, cases and independent effects remain unchanged."}
    if reviewed_http:
        review["decisions"]["business"]["reason"] = "Native application/state code and protected expectations remain byte-identical. The HTTP integration is checked against an exact import/server-factory/MIME-only patch from HEAD; it changes local viewer transport, with no business route, command, authorization, parameter, state or effect change. Full native scenarios remain required."
    review["decisions"]["state_machine"] = {"action": "unchanged", "reason": "No native state, transition, guard, activity, join or resource definition changed."}
    review["decisions"]["abstraction"] = {"action": "unchanged", "reason": "Node IDs, meanings, source bindings and lifecycle definitions remain unchanged. Managed source fingerprints are refreshed only after explicit impact review."}
    review["decisions"]["probes"] = {"action": "updated", "reason": "The managed receiver rereads declaration bytes at every admission, reusing the canonical comparison only for equal previously checked content. The isolated profile improves from 23.75 to 18.82 ms/event. Same-stat edits, formatting equivalence, malformed/missing definitions and outside paths have dedicated regressions. Existing emitter locations, fields, health, timeout boundaries, business assertions and on/off/fault modes are retained."}
    if MANAGED_REASON:
        review["decisions"]["probes"]["reason"] = MANAGED_REASON
    (root / CHANGE / "review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    verified = run(root, cli, "verify", "--root", ".")
    accepted = run(root, cli, "accept", "--root", ".")
    checked = run(root, cli, "check", "--root", ".")
    shutil.copytree(root / CHANGE, root / ".release/stategraph" / Path(CHANGE).name)
    shutil.copyfile(root / ".stategraph/active.json", root / ".release/stategraph/active.json")
    shutil.copyfile(root / cfg["manifest"], root / ".release/manifest.json")
    receipts.append({"project": name, "candidate_id": impact["candidate_id"], "verify": verified, "accept": accepted, "check": checked})
    print(name + " verified, accepted and frozen", flush=True)
(OUT / ("example-" + Path(CHANGE).name + "-" + sys.argv[1] + ".json")).write_text(json.dumps(receipts, indent=2) + "\n", encoding="utf-8")
