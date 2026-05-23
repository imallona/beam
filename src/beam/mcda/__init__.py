"""beam.mcda: multi-criteria decision analysis on a tool by metric matrix."""

from .aggregate import rank, weighted_sum
from .cd import (
    CriticalDifferenceReport,
    critical_difference,
    nemenyi_critical_difference,
)
from .cross_dataset import aggregate_across_datasets
from .facade import Result, run, run_from_registry
from .normalize import (
    STRATEGIES,
    min_max_normalize,
    normalization_warnings,
    normalize,
)
from .perturbation import (
    PairPerturbation,
    WeightPerturbationReport,
    smallest_weight_perturbation,
)
from .sensitivity import SensitivityReport, leave_one_metric_out
from .smaa import SMAAReport, smaa
from .topsis import topsis
from .validate import IncompatibleScaleError, validate_for_aggregation
from .weights import entropy_weights, equal_weights

__all__ = [
    "STRATEGIES",
    "CriticalDifferenceReport",
    "IncompatibleScaleError",
    "PairPerturbation",
    "Result",
    "SMAAReport",
    "SensitivityReport",
    "WeightPerturbationReport",
    "aggregate_across_datasets",
    "critical_difference",
    "entropy_weights",
    "equal_weights",
    "leave_one_metric_out",
    "min_max_normalize",
    "nemenyi_critical_difference",
    "normalization_warnings",
    "normalize",
    "rank",
    "run",
    "run_from_registry",
    "smaa",
    "smallest_weight_perturbation",
    "topsis",
    "validate_for_aggregation",
    "weighted_sum",
]
