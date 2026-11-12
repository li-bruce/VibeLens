# Dependency delivery and release

Request: keep third-party viewer code out of the Skill source/package, download
the reviewed version from a CDN first and fall back to GitHub, then merge and
release the completed model-network work with this delivery change.

1. Preserve the current example baselines and dependency byte identities.
2. Add one pinned manifest and a standard-library downloader, with verified cache
   reuse, atomic writes, bounded downloads, explicit offline/repair modes and
   no application-source writes.
3. Remove downloaded bundles from tracked source and default distribution;
   retain licenses, build locks, provenance and corresponding-source access.
4. Connect setup to installation, first viewer use, repository checks and Pages;
   keep a separate optional offline package.
5. Test primary/fallback delivery, corrupted/missing assets, cache reuse,
   distribution parity, native integration and the real 2D/3D viewer. Revalidate
   managed examples and the clean Git export without relaxing existing gates.
6. Publish release notes, merge to main and tag the new release. Check GitHub
   release artifacts and Pages deployment.

Business rules, stable graph identities, execution ownership, native adapter
contents and observation acceptance requirements remain unchanged.
