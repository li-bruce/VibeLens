# Replaceable routing dependencies

The viewer loads `routing-libavoid.vendor.js` and `libavoid.wasm` as separate files. They are unchanged files from libavoid-js 0.4.5, licensed LGPL-2.1-or-later. They are not embedded in the application or merged into a proprietary bundle. Users may replace either file and debug their modified library. `ROUTING-LICENSES.txt` retains the distributed license texts.

[libavoid-sources.zip](libavoid-sources.zip) contains the pinned wrapper, WebIDL inputs, build scripts and native libavoid source. [Provenance](libavoid-provenance.json) records upstream archive hashes and commits. The upstream build script selects adaptagrams v1.0.4, applies its forward-declaration patch and uses `emscripten/emsdk:3.1.36`. It obtains the binder from `https://gitlab.com/Aksem/webidl-embindgen.git`; that tool's revision is not pinned by upstream. The supplied npm binary has been browser-tested; a byte-identical native rebuild has not been established.

To build a modified library, unpack the source, follow `libavoid-js/README.md` and `tools/generate.py`, then run its npm build. To build the viewer distributions from this repository, run `npm ci` and `node build.mjs` under `tools/routing`. The Node smoke loader abort observed during investigation is preserved in the review evidence; production routing runs in a browser module worker.

`routing-tools.vendor.js` contains ISC/MIT D3, RBush and ngraph utilities, with complete notices alongside the bundle. It does not contain libavoid. Tabler SVGs are converted at build time by `tools/routing/build-icons.mjs`; the resulting volumetric models are VibeLens adaptations, not an official Tabler 3D model collection.
