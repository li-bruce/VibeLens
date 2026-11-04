# Public publication check

Snapshot: 2026-11-04, after publishing `092514751e3caeec8f25675bfaea40f74fe15860`.
This read-only check uses public GitHub REST responses. It is separate from the
passing local release gates and the requested new-chat trial.

## Confirmed publication

- Public `main` points to the release commit. Annotated tag `v0.11.0` resolves
  to the same commit; see [refs](public-refs-01.json) and
  [tag object](public-tag-object-01.json).
- [Publish release](https://github.com/li-bruce/VibeLens/actions/runs/41779931553)
  succeeded. The public [v0.11.0 release](https://github.com/li-bruce/VibeLens/releases/tag/v0.11.0)
  contains `vibelens-v0.11.0.zip`, 3,434,874 bytes, with GitHub-reported SHA-256
  `d8e293af14b178652e2b0e056dd56e5d35830cea4cbebe263ed77eaf1d817e15`.
  See [release metadata](public-release-01.json).

## Material CI findings

Both current Checks runs have failures; neither is a passing remote gate:

| Run | Confirmed failing job/step at snapshot |
| --- | --- |
| [Main push](https://github.com/li-bruce/VibeLens/actions/runs/41779931845) | `timeline-browser`: `npx playwright install --with-deps chromium` |
| [Tag push](https://github.com/li-bruce/VibeLens/actions/runs/41779931584) | The same browser installation step, plus Windows `python tools/check_source.py --format` |

Other jobs were still running when [their public states](current-release-jobs-01.json)
were captured. Ubuntu source quality had passed. These are intermediate job
states, not completed-run conclusions.

The older [f066ec4d run](https://github.com/li-bruce/VibeLens/actions/runs/41416153392)
failed at the same two steps; its six other jobs passed. See
[historical jobs](historical-otel-jobs-01.json) and
[annotations](historical-otel-check-annotations-01.json). Public annotations
report exit code 1 without the underlying error. Anonymous log downloads return
403; [the access result](public-log-access-01.json) is retained. The exact causes
must be taken from authenticated job logs, not inferred from those annotations.

## Pages

`pages.yml` is active and supports `workflow_dispatch`. At the snapshot there
was no Pages run for this release; its latest completed run still published
`4a2d615a`. See [workflow states](public-workflows-01.json) and
[Pages runs](public-pages-runs-01.json).

The release commit changes 764 files. The first file matching the Pages path
filter is at sorted index 463, and none appears in the first 300; see
[the local path inventory](pages-path-filter-01.json). This alone does not prove
why GitHub skipped the workflow. Current [GitHub Actions documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#git-diff-comparisons)
describes a 3,000-file path-filter limit, so an older 300-file explanation is
not established here. Dispatching the existing workflow is the direct recovery;
this reviewer performed no dispatch or other remote mutation.

Subsequent repairs and reruns must retain these first failed states and receive
their own evidence filenames. Published assets, a pending new-chat trial and
remote CI results remain distinct claims.
