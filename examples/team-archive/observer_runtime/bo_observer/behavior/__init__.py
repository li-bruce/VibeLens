"""Behavior definition checks, separate from native execution and observation.

Definition, binding, native-witness and iteration services share typed concepts.
This entry point assesses definitions only. Native execution remains with the
application; optional finite-model exploration is owned by the analysis package.
"""

from .contract import assess

__all__ = ["assess"]
