# CI portability repair

The first published v0.11.0 checks retained two infrastructure/tool failures:

- [Windows source-quality output](ci-windows-source-quality-09251475.log):
  the formatters passed, then the command failed while printing Black's Unicode
  output through a CP1252 console. The CLI now writes UTF-8; the regression
  also preserves a real failing tool's exit and report.
- [Browser installation](ci-timeline-browser-09251475.log): the moving
  `ubuntu-latest` label selected Ubuntu 26.04, unsupported by pinned Playwright
  1.56.1. The browser job now uses Ubuntu 24.04. Versions and browser tests stay
  unchanged.

The [six focused regressions](../ci-tool-portability-regression-01.json) and
[full source gate](../ci-tool-portability-source-01.json) passed. Actual formatter
output also passed through a strict legacy console; see the separately retained
reproduction and retest in this directory.

The existing Pages workflow was manually dispatched for `main` after automatic
deployment did not start. Run `41780469512` completed successfully; the public
homepage returned HTTP 200 and its v0.11.0 release link. The cause of the skipped
automatic run remains unconfirmed.

These changes affect repository verification only. They do not alter the
published Skill tree `ac38d114bf4c553388d697d0bfd76eeddcd51bed`.
The separate equal-clock concurrency finding is a product repair, tracked in the
next patch rather than concealed by changing the old assertion or adding sleeps.
