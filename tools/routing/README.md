# Viewer routing and icons

This directory builds the small dependencies distributed with the graph viewer. Node/npm are development tools; users of the bundled viewer do not need them for rendering.

```powershell
npm ci
node build.mjs
node build-icons.mjs
```

`build.mjs` bundles ISC/MIT spatial/search utilities and copies the unmodified, separately replaceable libavoid JS/Wasm. `build-icons.mjs` samples 19 selected MIT Tabler icons into shared vector centerlines. Three.js constructs their volumetric meshes at runtime; the complete Tabler pack is not shipped.

The application code lives under `skills/vibelens/assets/stategraph-viewer`: scene adapters, worker/client lifecycle, routing policy, navigation channels, collision geometry and picking are separate modules. Read `docs/source-guide.en.md` and `skills/vibelens/references/spatial-graph.md` from the repository root.

After a dependency upgrade, review licenses and output hashes in `tools/check_package.py` and the examples' explicit vendor registries. Run `tools/test_routing_controls.mjs`, `tools/test_routing_browser.mjs`, the viewer regressions, large-graph performance checks and both strict examples. An altered vendor file must continue to fail its hash check. Source/replacement notes for the LGPL dependency are in `skills/vibelens/references/vendor/README.md`.
