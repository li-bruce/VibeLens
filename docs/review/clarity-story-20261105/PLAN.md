# Trial assessment, implementation detail and product story

## Scope

1. Review the completed public v0.12.1 trial against its actual evidence. Preserve failed formal acceptance and untested iteration separately from passing business checks.
2. Separate implementation display into entry points, project structure and code execution. Preserve semantic identities, capture roles, saved exclusions, cross-layer paths and Timeline correspondence.
3. Replace the product home with a concise explanation of the problem, the connected graph and the development loop. Keep English as default and Chinese as a switch.
4. Rework the file-sharing walkthrough around one question: why can the recipient still download after revocation? Present the story in conversation before taking screenshots. Keep Codex development separate from app operations and VibeLens investigation.
5. Run classification/migration, native demo and browser regressions. Inspect desktop/mobile screenshots and retain findings.

## Design

- Paper-white background, charcoal type, teal primary accent; semantic colors only inside the graph.
- Large editorial headings, short readable paragraphs, generous whitespace, thin rules. No repeated feature-card grid.
- A single connected graph is the signature visual. The home explains its purpose; the demo demonstrates one diagnosis.
- Natural scrolling, keyboard access, reduced-motion support, and a persistent native viewer between story steps.
- Keep actual execution data immutable. Curated explanations and overview diagrams are presentation only.

## Status

- [x] Completed trial reviewed; three acceptance gaps identified.
- [x] Story presented in the coordinating conversation before screenshot capture.
- [x] Implementation display refinement and compatibility checks.
- [x] Home and walkthrough redesign.
- [x] Browser interaction, responsive and localization checks.
- [x] Evidence and final assessment.

The completed trial does not prove a later business iteration or exhaustive UI coverage. This page redesign must not turn those missing results into a release claim.

## Interaction follow-up

- [x] Reproduce the CI custom-view failure and keep its original evidence.
- [x] Preserve the chapter while a visible editor is in use; release it for scrolling and navigation.
- [x] Replace the full-width change list with a movable compact panel, with two preview rows and full detail disclosure.
- [x] Recheck shipped viewer copies and both clean exported example installations.
- [x] Preserve the reader's chapter during language changes and recheck the complete walkthrough after the Linux CI mobile failure.
- Publication status is checked on the pushed commit in GitHub Actions; the final delivery links that run and the published pages.
