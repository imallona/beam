"""beam.mcda: multi-criteria decision analysis on a tool by metric matrix."""

from ._missing import IncompleteMatrixError
from .aggregate import rank, weighted_sum
from .aggregation_agreement import (
    AggregationAgreementReport,
    aggregation_agreement,
)
from .cd import (
    CriticalDifferenceReport,
    critical_difference,
    nemenyi_critical_difference,
)
from .comet import comet
from .cross_dataset import aggregate_across_datasets, reduce_tensor
from .facade import RegistryContext, Result, registry_context, run, run_from_registry
from .metric_validity import MetricValidityReport, metric_validity
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
from .promethee import promethee_ii
from .reference_levels import (
    MetricBaseline,
    NoiseFloorReport,
    PairSeparation,
    RandomBaselineReport,
    beats_random_baseline,
    noise_floor_separation,
)
from .reliability import MetricReliabilityReport, metric_reliability
from .sensitivity import (
    DatasetSensitivityReport,
    SensitivityReport,
    leave_one_dataset_out,
    leave_one_metric_out,
)
from .skillings_mack import (
    SkillingsMackReport,
    coverage_aware_critical_difference,
    skillings_mack,
)
from .smaa import SMAAReport, smaa
from .topsis import topsis
from .validate import IncompatibleScaleError, validate_for_aggregation
from .vikor import vikor
from .weights import (
    InconsistentPairwiseMatrixError,
    ahp_weights,
    critic_weights,
    entropy_weights,
    equal_weights,
    merec_weights,
    standard_deviation_weights,
)

__all__ = [
    "STRATEGIES",
    "AggregationAgreementReport",
    "CriticalDifferenceReport",
    "DatasetSensitivityReport",
    "IncompatibleScaleError",
    "IncompleteMatrixError",
    "InconsistentPairwiseMatrixError",
    "MetricBaseline",
    "MetricReliabilityReport",
    "MetricValidityReport",
    "NoiseFloorReport",
    "PairPerturbation",
    "PairSeparation",
    "RandomBaselineReport",
    "RegistryContext",
    "Result",
    "SMAAReport",
    "SensitivityReport",
    "SkillingsMackReport",
    "WeightPerturbationReport",
    "aggregate_across_datasets",
    "aggregation_agreement",
    "ahp_weights",
    "beats_random_baseline",
    "comet",
    "coverage_aware_critical_difference",
    "critic_weights",
    "critical_difference",
    "entropy_weights",
    "equal_weights",
    "leave_one_dataset_out",
    "leave_one_metric_out",
    "merec_weights",
    "metric_reliability",
    "metric_validity",
    "min_max_normalize",
    "nemenyi_critical_difference",
    "noise_floor_separation",
    "normalization_warnings",
    "normalize",
    "promethee_ii",
    "rank",
    "reduce_tensor",
    "registry_context",
    "run",
    "run_from_registry",
    "skillings_mack",
    "smaa",
    "smallest_weight_perturbation",
    "standard_deviation_weights",
    "topsis",
    "validate_for_aggregation",
    "vikor",
    "weighted_sum",
]
