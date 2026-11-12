"""Prepare pinned viewer resources for repository examples, tests and Pages.

Only downloaded assets are materialized. This command never regenerates source
bindings, upgrades managed code or changes a frozen acceptance record.
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.delivery.dependencies import ensure_assets, LOCK_NAME

EXAMPLE_VIEWERS = (
    "examples/delivery/integrations/bo_view",
    "examples/delivery/observer_generated/static",
    "examples/team-archive/static/graph",
)


def setup_examples(root=ROOT, **options):
    """Restore dependencies identified by each example's committed lock file."""
    for name in EXAMPLE_VIEWERS:
        assets = root / name
        if (assets / LOCK_NAME).is_file():
            ensure_assets(assets, **options)


def setup(**options):
    ensure_assets(ROOT / "skills/vibelens/assets/stategraph-viewer", **options)
    setup_examples(**options)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    setup(offline=args.offline)
    print("Pinned viewer assets are ready.")
