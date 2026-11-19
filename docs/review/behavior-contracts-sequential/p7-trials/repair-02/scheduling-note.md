# Runner scheduling

The first full runner was interrupted before its managed-example stage because
the separate managed-example review was still active. This avoids overlapping
writes to shared example verification artifacts. The partial log is retained;
it is neither a passed full regression nor a product failure. The full runner
will be restarted after the review finishes.
