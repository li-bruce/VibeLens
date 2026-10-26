"""Gallery behavior. Observation is supplied through a small optional port.

The repository owns transactions. Policy decides whether the requested review
can be applied; the application reads that result before changing any data.
"""

import base64
from contextlib import nullcontext

from policy import approval_policy


class Gallery:
    """One artwork with versioned uploads, review messages and a public exhibit."""

    def __init__(self, repository, observer=None):
        self.repository = repository
        self.bo = observer

    def call(self, node, function, values):
        """Keep instrumentation optional; call exactly the same business function."""
        return self.bo.call(node, function, values) if self.bo else function(**values)

    def upload(self, actor, title, image):
        """Validate a real PNG header and keep each replacement as a new version."""
        if actor != "artist":
            return {"status": "forbidden"}
        try:
            raw = base64.b64decode(image, validate=True)
        except ValueError:
            return {"status": "invalid_image"}
        valid = self.call("image-check", valid_image, {"raw": raw})
        if not valid:
            return {"status": "invalid_image"}
        version = self.repository.save_upload(title, raw)
        return {"status": "pending", "image_version": version}

    def preview(self, actor):
        """Return the exact version the reviewer opened, for the next request."""
        if actor != "reviewer":
            return {"status": "forbidden"}
        row = self.repository.read_artwork()
        return {"status": row["status"], "reviewed_version": row["image_version"]}

    def approve(self, actor, reviewed_version):
        """Check the submitted review against current data inside one transaction."""
        context = self.bo.transaction() if self.bo else nullcontext()
        with context:
            with self.repository.engine.begin() as connection:
                row = self.repository.read_artwork(connection)
                if row["image_version"] == 0:
                    return {"status": "no_image"}
                verdict = self.call(
                    "review-policy",
                    approval_policy,
                    {
                        "actor": actor,
                        "current_version": row["image_version"],
                        "reviewed_version": reviewed_version,
                    },
                )
                if verdict != "allowed":
                    return {
                        "status": verdict,
                        "image_version": row["image_version"],
                        "reviewed_version": reviewed_version,
                    }
                selected = self.call(
                    "choose-version", choose_version, {"current_version": row["image_version"]}
                )
                self.repository.publish(connection, selected)
        return {
            "status": "displayed",
            "image_version": selected,
            "reviewed_version": reviewed_version,
            "published_version": selected,
        }


def valid_image(raw):
    """Accept the PNG fixture format; production image decoding is outside this demo."""
    return len(raw) >= 24 and raw.startswith(b"\x89PNG\r\n\x1a\n") and raw[12:16] == b"IHDR"


def choose_version(current_version):
    """Select the persisted revision after the policy has allowed the operation."""
    return current_version
