"""beam.heterogeneity: method-dataset heterogeneity diagnostics.

A global MCDA ranking pools a heterogeneous set of datasets into one
recommendation. This subpackage qualifies that ranking by asking where it
fails: how much of the score variation is a method-by-dataset interaction
rather than a stable method effect, and which dataset properties reverse the
ranking. It is the technical answer to the "against one method fits all"
critique (Strobl and colleagues).

The tools all wrap R in a one-shot subprocess:

- ``mixed_effects``: a variance decomposition (Eugster, Hothorn and Leisch
  2008) that splits the score variation into a method effect, a between-dataset
  shift, and a method-by-dataset interaction. Gated by ``r_available`` (lme4);
  pass ``engine="glmmtmb"`` for a beta family on bounded metrics, gated by
  ``glmmtmb_available``.
- ``bradley_terry_tree``: a Bradley-Terry tree (Strobl, Wickelmaier and
  Zeileis) that splits the datasets by their features so each leaf has its own
  method ranking, flagging where the pooled ranking reverses. Gated by
  ``bttree_available`` (psychotree).
- ``plackett_luce``: a Plackett-Luce model for full or partial rankings, with
  per-method worth and quasi-standard errors. Gated by
  ``plackett_luce_available`` (PlackettLuce).
- ``source_variance_decomposition``: a cross-benchmark decomposition that
  separates the method-by-benchmark disagreement from method-by-dataset
  variation. Gated by ``r_available`` (lme4).
- ``network_meta_analysis``: a network meta-analysis that pools the direct and
  indirect evidence across benchmarks scoring overlapping methods into one
  coherent ranking, with heterogeneity and inconsistency statistics. Gated by
  ``netmeta_available`` (netmeta).
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
    glmmtmb_available,
    mixed_effects,
    mixed_effects_from_matrix,
    r_available,
)
from .network_meta import (
    NetworkMetaReport,
    netmeta_available,
    network_meta_analysis,
)
from .plackett_luce import (
    PlackettLuceReport,
    plackett_luce,
    plackett_luce_available,
    rankings_from_matrix,
)
from .source_variance import (
    SourceVarianceReport,
    source_variance_decomposition,
)

__all__ = [
    "BTNode",
    "BradleyTerryTreeReport",
    "MixedEffectsReport",
    "NetworkMetaReport",
    "PlackettLuceReport",
    "RExecutionError",
    "RNotAvailableError",
    "SourceVarianceReport",
    "bradley_terry_tree",
    "bttree_available",
    "glmmtmb_available",
    "mixed_effects",
    "mixed_effects_from_matrix",
    "netmeta_available",
    "network_meta_analysis",
    "paired_comparisons",
    "plackett_luce",
    "plackett_luce_available",
    "r_available",
    "rankings_from_matrix",
    "source_variance_decomposition",
]
