"""Behavior definition checks, separate from native execution and observation.

The first P1 slice validates a source-free contract against existing concepts.
It does not migrate projects, execute actions or certify finite exploration.
"""

from .contract import assess

__all__ = ["assess"]
