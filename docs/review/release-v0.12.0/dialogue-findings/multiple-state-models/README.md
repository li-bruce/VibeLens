# Multiple state models: retained capability rejection

Date: 2026-11-05. Source: the independent fresh-install trial, chat
`01a1a757-9d29-7500-966c-db0e29a7651b`, round 02. The requirement-side answers are
user-authorized simulated dialogue, not independent human acceptance.

The file-sharing draft defines three distinct state subjects: `session`
(`session_id`), `file_review` (`file_id`) and `sharing` (`share_id`). Its structure
is valid. The unchanged v0.12.0 native binding checker rejects the combined scope:

```text
unsupported_multiple_bound_state_models: file_review,session,sharing
```

Draft authoring supports several models; the released binding compares one
`primary_state_model` with one native `model.machine`. The observation module,
native anchors and instance/export checks also use that single declaration.
Removing the rejection alone would not provide correct multi-model support.

## Evidence and reproduction

The four JSON files beside this note are byte-preserved copies from the trial's
`review/round-02/`. [provenance.json](provenance.json) records their source paths,
SHA-256 hashes and the installed release archive hash.

- [discovery.presented.json](discovery.presented.json): retained three-model draft.
- [multiple-state-binding-input.json](multiple-state-binding-input.json): exact
  selected scope and empty native carrier used to probe the capability.
- [multiple-state-binding-full-report.json](multiple-state-binding-full-report.json):
  all errors, including missing confirmation and implementation evidence.
- [multiple-state-binding-summary.json](multiple-state-binding-summary.json):
  the target rejection and the original trial's evidence boundary.

The carrier is deliberately not a working application. This is a capability
reproduction, not a failed runtime test or a complete implementation assessment.
The retained draft's semantic revision matches the recorded checker input. A
read-only rerun with the unmodified installed release reproduced the entire
retained report exactly.

From the repository root, using an interpreter with the Skill requirements:

```powershell
@'
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path("skills/vibelens/scripts").resolve()))
from bo_observer.concepts import check_binding, snapshot
root = Path("docs/review/release-v0.12.0/dialogue-findings/multiple-state-models")
doc = json.loads((root / "discovery.presented.json").read_text(encoding="utf-8"))
data = json.loads((root / "multiple-state-binding-input.json").read_text(encoding="utf-8"))
assert snapshot(doc, data["scope"])["semantic_revision"] == data["binding"]["semantic_revision"]
report = check_binding(doc, data["model"], data["binding"], scope=data["scope"])
print(json.dumps(report, indent=2))
assert any(e["code"] == "unsupported_multiple_bound_state_models" for e in report["errors"])
'@ | python -B -
```

Exit 0 means the expected rejection was reproduced; `report.valid` remains false.
No validator, runtime declaration or confirmation is replaced by this command.

## Guidance change and subsequent trial scope

The Skill now checks binding and executor capabilities before asking to confirm
implementation scope. It retains unsupported designs and their complete checker
reports, then requires an explicit scope revision or a canonical extension.

The subsequent simulated reply explicitly selects one formal `file_review` drive
machine. Sessions and recipient grants retain separate identities, policy facts
and required real observations. The original business requirements remain in
scope. This revised trial does not claim complete native transition/guard/effect
binding for the other two object lifecycles. Its eventual implementation results
belong to later trial evidence; they are not established by this note.

The published v0.12.0 archive remains unchanged. This guidance adjustment neither
implements multi-model native binding nor relaxes its rejection.
