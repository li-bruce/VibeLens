# Local tool dependencies

The standard integration runs the viewer, layout engines, routing libraries and
Python observer from the installed VibeLens package. They serve local debugging
and are not copied into the user's business project or production application.
`bo_integrate.py` installs only the native state/probe adapters (seven small
standard-library Python files, or two JavaScript modules), with a hash receipt.
Project-owned declarations, wiring, tests and private view configuration remain
in the project. Optional database/telemetry integrations add their selected native
dependencies explicitly.

Historical full-copy examples contain viewer assets as test fixtures. They retain
their notices and require a reviewed migration; the lightweight installer does
not silently delete them. Embedding and distributing the viewer in another product
is a separate integration, outside this default boundary.

## Downloading instead of bundling

The Skill does **not** require whole third-party packages in its source tree.
Python and parser dependencies already install from pinned requirements and npm
lockfiles. Viewer packages can likewise be downloaded by exact version with
integrity checks, then built or copied to the tool installation/cache. Install
scripts should report missing assets clearly and keep an offline package option.

This branch keeps the reviewed offline viewer bundles. It does not silently
change existing installation requirements or claim a new automatic download hook.
A generic Skill installer may only copy files; the supported setup is an explicit
initialization command in the host workflow. Repository maintainers can reproduce
bundles with `npm ci` followed by the checked-in build script in `tools/routing`
or `tools/spatial`. Lockfiles fix dependency resolution; bundle hash checks in
`tools/check_package.py` verify the distributed bytes. These steps run in the
VibeLens repository, not the user's application.

The [Agent Skills specification](https://agentskills.io/specification) defines
files, scripts and compatibility metadata, without a universal installation
hook. The exact-version installation behavior is described in
[npm ci](https://docs.npmjs.com/cli/v11/commands/npm-ci/).

## License scope

VibeLens's original code uses MIT. Third-party components retain their own terms:
libavoid-js uses LGPL-2.1-or-later and ELK uses EPL-2.0. Local debugging describes
the intended deployment; it does not turn those libraries into MIT code or remove
redistribution obligations. Commercial application development is not prohibited.
Keep the existing notices and corresponding source/replacement materials when
redistributing the viewer. Downloading at setup changes delivery, not licensing.

See [routing provenance and replacement](vendor/README.md) and the
[LGPL 2.1 text](https://opensource.org/license/lgpl-2-1). The current upstream Wasm
matches the reviewed package bytes; a byte-identical native rebuild remains
unconfirmed. This branch does not relabel that evidence.
