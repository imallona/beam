"""Ontology-aware validation gating the MCDA pipeline.

Checks whether the requested aggregation is licit for the declared scale
types and allowed transformations of the metric cards being aggregated.
The rules enforced here are the working contract between the metric
registry and the pipeline.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..cards import MetricProperties

_ARITHMETIC_METHODS = ("saw", "topsis")
_MIN_MAX_LICIT_TRANSFORMS = frozenset({"affine", "min_max"})


class IncompatibleScaleError(ValueError):
    """Raised when a metric's declared scale type forbids the requested aggregation."""


def validate_for_aggregation(
    properties: Sequence[MetricProperties],
    method: str,
) -> None:
    """Refuse aggregations that are not licit given the declared metric properties.

    Two rules, applied per column:

    1. Scale type. SAW and TOPSIS rely on weighted arithmetic on the
       normalised matrix. A nominal column has no meaningful order and an
       ordinal column has no meaningful unit, so neither method is licit.
       Only interval and ratio scales pass.
    2. Allowed transformations. The pipeline applies a min-max
       transformation in ``min_max_normalize`` before any aggregation. The
       column's allowed_transformations must include either ``affine``
       (the family that contains min-max) or the explicit ``min_max``
       label.

    Raises ``IncompatibleScaleError`` on the first failing column with a
    message naming the metric id, the offending field, and the rule that
    rejected it.
    """
    if method not in _ARITHMETIC_METHODS:
        raise ValueError(f"unknown method {method!r}; validation only knows {_ARITHMETIC_METHODS}")

    for prop in properties:
        if prop.scale_type not in ("interval", "ratio"):
            raise IncompatibleScaleError(
                f"metric {prop.id!r}: scale_type {prop.scale_type!r} is not licit for "
                f"{method!r} aggregation (need interval or ratio)"
            )
        if not _MIN_MAX_LICIT_TRANSFORMS.intersection(prop.allowed_transformations):
            raise IncompatibleScaleError(
                f"metric {prop.id!r}: allowed_transformations "
                f"{list(prop.allowed_transformations)!r} does not include "
                f"'affine' or 'min_max', so min-max normalisation is not licit"
            )
