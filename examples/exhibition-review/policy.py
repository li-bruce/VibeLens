"""Authorization for publishing an image."""


def approval_policy(actor, current_version, reviewed_version):
    """Only a reviewer who opened the current image may publish it."""
    if actor != "reviewer":
        return "forbidden"
    if reviewed_version != current_version:
        return "stale_review"
    return "allowed"
