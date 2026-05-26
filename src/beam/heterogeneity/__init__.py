"""beam.heterogeneity: method-dataset heterogeneity diagnostics.

A global MCDA ranking pools a heterogeneous set of datasets into one
recommendation. This subpackage qualifies that ranking by asking where it
fails: how much of the score variation is a method-by-dataset interaction
rather than a stable method effect, and which dataset properties reverse the
ranking. It is the technical answer to the "against one method fits all"
critique (Strobl and colleagues).

Two tools are available, both wrapping R in a one-shot subprocess (ADR 0009):

- ``mixed_effects``: a variance decomposition (Eugster, Hothorn and Leisch
  2008) that splits the score variation into a method effect, a between-dataset
  shift, and a method-by-dataset interaction. Gated by ``r_available`` (lme4).
- ``bradley_terry_tree``: a Bradley-Terry tree (Strobl, Wickelmaier and
  Zeileis) that splits the datasets by their features so each leaf has its own
  method ranking, flagging where the pooled ranking reverses. Gated by
  ``bttree_available`` (psychotree).

The Plackett-Luce extension named in PLAN Phase 4 is not implemented yet.
"""

from .bradley_terry import (
    BradleyTerryTreeReport,
    BTNode,
    bradley_terry_tree,
    bttree_available,
    paired_comparisons,
)
from .mixed_effects import (
    MixedEffectsReport,
    RExecutionError,
    RNotAvailableError,
    mixed_effects,
    mixed_effects_from_matrix,
    r_available,
)

__all__ = [
    "BTNode",
    "BradleyTerryTreeReport",
    "MixedEffectsReport",
    "RExecutionError",
    "RNotAvailableError",
    "bradley_terry_tree",
    "bttree_available",
    "mixed_effects",
    "mixed_effects_from_matrix",
    "paired_comparisons",
    "r_available",
]
