# Observed design-view label overlap

Status: observed in this trial; cause not established. No maintained or installed viewer source was patched.

## Reproduction

1. Use the exact local Skill recorded in `skill-source.json` and this project's updated `discovery.json`.
2. Start the canonical `scripts/bo_web.py serve --root PROJECT --port 62428` on the host. The functioning host process is recorded in `design-host-server.json`.
3. Record `zh-CN` with the canonical language command and use the conversation focus recorded under `bo_stategraph/config/design-focus.json`.
4. Open `http://127.0.0.1:62428/graph` in the in-app browser and reload after the actual answers have updated the design.
5. At the displayed default 2D layout and 41% zoom in the 1280 by 720 browser viewport, inspect the upload and privileged-access labels in the lower-right central area.

## Actual result

The labels for upload with reviewer selection and uploader/reviewer file access overlap and are difficult to distinguish. Other long labels are crowded. The semantic browser tree still exposes the correct separate labels and relations.

Actual artifacts: `design-round2.png` and `browser-round2.txt`. This is presentation evidence only. It does not establish a missing permission check, a business failure, a canonical data error, or a runtime capture problem. No layout control, custom view, or framework workaround was applied to hide the issue.

## Separate environment finding

Initial local connection timeouts were associated with sandbox execution and service launching. Independent host HTTP requests and the in-app browser later succeeded. These timeouts are not used as evidence for this presentation issue or a framework networking defect.
