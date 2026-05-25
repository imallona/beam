"""beam.heterogeneity: method-dataset heterogeneity diagnostics.

A global MCDA ranking pools a heterogeneous set of datasets into one
recommendation. This subpackage qualifies that ranking by asking where it
fails: how much of the score variation is a method-by-dataset interaction
rather than a stable method effect. It is the technical answer to the
"against one method fits all" critique (Strobl and colleagues).

The first tool is a mixed-effects variance decomposition (Eugster, Hothorn
and Leisch 2008), wrapping R's lme4 in a one-shot subprocess. Use
``r_available`` to check the R toolchain before calling ``mixed_effects``.
The Bradley-Terry trees and the Plackett-Luce extension named in PLAN
Phase 4 are not implemented yet.
"""

from .mixed_effects import (
    MixedEffectsReport,
    RExecutionError,
    RNotAvailableError,
    mixed_effects,
    mixed_effects_from_matrix,
    r_available,
)

__all__ = [
    "MixedEffectsReport",
    "RExecutionError",
    "RNotAvailableError",
    "mixed_effects",
    "mixed_effects_from_matrix",
    "r_available",
]
