# Pages: conversation-scoped usage

The homepage now explains activation in the current conversation and shows three
view instructions: focus a business path, open a decision's values, and filter a
recording. English and Chinese share the same examples and controls. Installation
includes a copyable prompt beginning with `$vibelens`.

## What the example runs

The embedded canvas uses the shipped VibeLens viewer and its conversation-control
bridge. `tools/build_control_preview.py` exports plans through the Python controller
and rechecks their identities and recording evidence. The source is the existing
`docs/site/case-data/v1.json` capture. The static website chooses among these checked
examples; it does not run Codex or interpret arbitrary text.

The first view retains three original business nodes and two relations. The detail
view includes the owning approval step and its decision. Replay selects six of the
82 original events; the underlying recording remains unchanged. Two-dimensional
and three-dimensional views use the native renderer. Offscreen replay pauses, and
reduced-motion mode requires an explicit playback action.

## Failures and retests

| Attempt | Finding | Change and result |
| --- | --- | --- |
| First browser run | Windows clipboard converted multiline text to CRLF; strict byte comparison failed. | Normalize CRLF in the clipboard assertion only. Prompt content and `$vibelens` checks remain strict. See [first failure](first-failure.json). |
| Narrower detail preview | A single child-node selection after the business-only view produced an empty canvas. | Keep the owning approval node in the preview's explicit selection and verify that the decision and both version inputs are visible. This fixes the website example; a general single-child selection repair is outside this Pages change. See [scope failure](preview-scope-failure.json). |
| Final local browser run | Both languages passed. | Business path, parameters, native 3D, exact recorded events, advancing filtered replay, copying, mobile layout, language switching and reduced motion. See [result](local/result.json). |

The original seven-step demonstration also passed in both languages, including
progressive graph confirmation, user actions in VibeLens, source drill-down, repair,
retained custom views and 3D camera interaction. See [existing demo](existing-demo.json).

Syntax, lint and formatting checks passed for 101 Python and 69 JavaScript modules.
The package check passed for 113 copied runtime modules and documentation links.
The Pages builder also ran with Python site packages disabled, matching its
dependency-free deployment environment. See [source checks](source-quality.json)
and [package result](package.log).

## Review images

![English usage preview](local/en-business.png)
![Native three-dimensional detail view](local/en-details-3d.png)
![Chinese activation prompt](local/zh-CN-activation.png)
![Chinese mobile layout](local/zh-CN-mobile.png)

## Publication

Publication receipts and a browser run against the public URL are retained after
deployment. This update changes Pages and usage documentation; it does not create
a release tag or replace the project's observer runtime.
