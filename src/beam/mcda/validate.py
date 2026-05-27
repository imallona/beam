"""Ontology-aware validation gating the MCDA pipeline.

Checks whether the requested aggregation, and the per-column normalization
it rests on, are licit for the declared scale types and allowed
transformations of the metric cards. These rules are the working contract
between the metric registry and the pipeline.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..cards import MetricProperties

_ARITHMETIC_METHODS = ("saw", "topsis", "vikor", "promethee_ii", "comet")

# The transform each normalization strategy applies, expressed as the set of
# allowed_transformations labels that license it. A column passes if its card
# permits any label in the set.
_STRATEGY_TRANSFORMS = {
    "min_max": frozenset({"affine", "min_max"}),
    "baseline_relative": frozenset({"affine", "min_max"}),
    "log_min_max": frozenset({"log"}),
    "rank": frozenset({"rank"}),
    "zscore": frozenset({"z_score", "affine"}),
    "target_relative": frozenset({"affine", "min_max"}),
}


class IncompatibleScaleError(ValueError):
    """Raised when a metric's declared scale type forbids the requested aggregation."""


def validate_for_aggregation(
    properties: Sequence[MetricProperties],
    method: str,
    strategies: Sequence[str] | None = None,
) -> None:
    """Refuse aggregations or normalizations that the metric cards do not license.

    Two rules, applied per column:

    1. Scale type. SAW, TOPSIS, VIKOR, PROMETHEE II and COMET all rely on
       weighted arithmetic on the normalized matrix. A nominal column has no
       order and an ordinal column has no unit, so none of these methods is
       licit on them. Only interval and ratio scales pass.
    2. Allowed transformations. The pipeline rescales each column with the
       strategy named in ``strategies`` (defaulting to ``min_max``). The
       card must permit the transform that strategy applies: ``affine`` or
       ``min_max`` for min_max, baseline_relative and target_relative,
       ``log`` for log_min_max, ``rank`` for rank, ``z_score`` or ``affine``
       for zscore.

    Raises ``IncompatibleScaleError`` on the first failing column, naming
    the metric id, the offending field, and the rule that rejected it.
    """
    if method not in _ARITHMETIC_METHODS:
        raise ValueError(f"unknown method {method!r}; validation only knows {_ARITHMETIC_METHODS}")

    properties = list(properties)
    if strategies is None:
        strategies = ["min_max"] * len(properties)
    elif len(strategies) != len(properties):
        raise ValueError(
            f"strategies has {len(strategies)} entries but properties has {len(properties)}"
        )

    for prop, strat in zip(properties, strategies, strict=True):
        if prop.scale_type not in ("interval", "ratio"):
            raise IncompatibleScaleError(
                f"metric {prop.id!r}: scale_type {prop.scale_type!r} is not licit for "
                f"{method!r} aggregation (need interval or ratio)"
            )
        if strat not in _STRATEGY_TRANSFORMS:
            raise ValueError(f"metric {prop.id!r}: unknown normalization strategy {strat!r}")
        licit = _STRATEGY_TRANSFORMS[strat]
        if not licit.intersection(prop.allowed_transformations):
            raise IncompatibleScaleError(
                f"metric {prop.id!r}: normalization {strat!r} needs one of "
                f"{sorted(licit)} in allowed_transformations, but the card lists "
                f"{list(prop.allowed_transformations)!r}"
            )
