"""Tests for the ontology-aware validation gate."""

import pytest

from beam.cards import MetricProperties
from beam.mcda import IncompatibleScaleError, validate_for_aggregation


def _ratio_props(metric_id="acc", allowed=("affine", "rank")):
    return MetricProperties(
        id=metric_id,
        polarity="higher_is_better",
        scale_type="ratio",
        range_lower=0,
        range_upper=1,
        allowed_transformations=tuple(allowed),
        recommended_aggregation_across_datasets="arithmetic_mean",
    )


def _interval_props(metric_id="ari", allowed=("affine", "rank")):
    return MetricProperties(
        id=metric_id,
        polarity="higher_is_better",
        scale_type="interval",
        range_lower=-1,
        range_upper=1,
        allowed_transformations=tuple(allowed),
        recommended_aggregation_across_datasets="arithmetic_mean",
    )


def test_accepts_interval_and_ratio_under_saw():
    validate_for_aggregation([_interval_props(), _ratio_props()], "saw")


def test_accepts_interval_and_ratio_under_topsis():
    validate_for_aggregation([_interval_props(), _ratio_props()], "topsis")


def test_rejects_nominal_scale():
    nominal = MetricProperties(
        id="nominal_thing",
        polarity="higher_is_better",
        scale_type="nominal",
        range_lower=None,
        range_upper=None,
        allowed_transformations=("rank",),
        recommended_aggregation_across_datasets=None,
    )
    with pytest.raises(IncompatibleScaleError, match="nominal_thing"):
        validate_for_aggregation([nominal], "saw")


def test_rejects_ordinal_scale():
    ordinal = MetricProperties(
        id="ordinal_thing",
        polarity="higher_is_better",
        scale_type="ordinal",
        range_lower=None,
        range_upper=None,
        allowed_transformations=("rank",),
        recommended_aggregation_across_datasets=None,
    )
    with pytest.raises(IncompatibleScaleError, match="ordinal"):
        validate_for_aggregation([ordinal], "topsis")


def test_rejects_missing_affine_and_min_max():
    no_min_max = MetricProperties(
        id="no_affine",
        polarity="higher_is_better",
        scale_type="ratio",
        range_lower=0,
        range_upper=1,
        allowed_transformations=("log", "rank"),  # neither affine nor min_max
        recommended_aggregation_across_datasets="geometric_mean",
    )
    with pytest.raises(IncompatibleScaleError, match="no_affine"):
        validate_for_aggregation([no_min_max], "saw")


def test_min_max_in_transformations_is_accepted():
    """The schema enum has both 'affine' and 'min_max'; either should pass."""
    only_min_max = _ratio_props(allowed=("min_max",))
    validate_for_aggregation([only_min_max], "saw")


def test_rejects_unknown_method():
    with pytest.raises(ValueError, match="unknown method"):
        validate_for_aggregation([_ratio_props()], "promethee")


def test_log_min_max_needs_log_in_transformations():
    """A ratio metric using log_min_max must declare log, not just affine."""
    only_affine = _ratio_props(allowed=("affine", "min_max"))
    with pytest.raises(IncompatibleScaleError, match="log_min_max"):
        validate_for_aggregation([only_affine], "saw", strategies=["log_min_max"])


def test_log_min_max_accepted_when_log_declared():
    has_log = _ratio_props(allowed=("log", "rank"))
    validate_for_aggregation([has_log], "saw", strategies=["log_min_max"])


def test_rank_strategy_needs_rank_transformation():
    no_rank = _ratio_props(allowed=("affine", "min_max"))
    with pytest.raises(IncompatibleScaleError, match="rank"):
        validate_for_aggregation([no_rank], "saw", strategies=["rank"])


def test_baseline_relative_passes_with_affine():
    validate_for_aggregation([_interval_props()], "saw", strategies=["baseline_relative"])


def test_strategies_length_must_match():
    with pytest.raises(ValueError, match="strategies has"):
        validate_for_aggregation([_ratio_props(), _interval_props()], "saw", strategies=["min_max"])
