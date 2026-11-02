# Human source-review concerns

Source: human steering received in the current chat on 2026-11-01. These are review concerns, not pre-established runtime failures.

1. Compare sign-out capture with the native session at the exact event boundary, retaining a coherent distinction between the initiating user and the principal remaining after session removal. Do not derive the earlier event from a later session state or fill null merely because the case is named sign-out.
2. Isolate and name observation-only principal/object helpers and job tracing carriers according to the `bo_` convention. Keep business code readable.
3. Exercise an unhandled exception through the real entrypoint so Flask actually returns HTTP 500. Capture the native business exception and actual response code. Prefer upstream Flask instrumentation; do not invent a response when an inner span ends before Flask handles the error.

Keep the maintained repository and copied canonical validators read-only. Preserve evidence before deciding whether a defect belongs to the application integration or shared framework.

At receipt, the application had already moved `session.clear` into the native sign-out interval via its callback. That source change still requires an independent event-time session witness. The other concerns are investigated against the saved current source hashes.
