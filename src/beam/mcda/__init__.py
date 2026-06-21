"""beam.mcda: multi-criteria decision analysis on a tool by metric matrix."""

from ._missing import IncompleteMatrixError
from .aggregate import rank, weighted_sum
from .aggregation_agreement import (
    AggregationAgreementReport,
    aggregation_agreement,
)
from .attribution import (
    AttributionReport,
    AttributionSetting,
    attribution_synthesis,
    setting_from_rank_sensitivity,
    setting_from_same_data_contrast,
    setting_from_source_variance,
)
from .bayesian import (
    BayesianSignReport,
    PairPosterior,
    bayesian_sign_comparison,
)
from .card_consistency import (
    CardDataConsistencyReport,
    ConsistencyFinding,
    MetricConsistency,
    card_data_consistency,
)
from .cd import (
    CriticalDifferenceReport,
    critical_difference,
    nemenyi_critical_difference,
)
from .comet import comet
from .cross_dataset import aggregate_across_datasets, reduce_tensor
from .dataset_concordance import (
    DatasetConcordanceReport,
    RankDeviation,
    dataset_concordance,
)
from .dataset_discrimination import (
    DatasetDiscriminationReport,
    dataset_discrimination,
)
from .diagnostics import MetricDiagnosticsReport, metric_diagnostics
from .difficulty_concordance import (
    DifficultyConcordanceReport,
    difficulty_concordance,
)
from .dimensionality import MetricDimensionalityReport, metric_dimensionality
from .facade import RegistryContext, Result, registry_context, run, run_from_registry
from .metric_validity import MetricValidityReport, metric_validity
from .normalization_agreement import (
    NormalizationAgreementReport,
    normalization_agreement,
)
from .normalize import (
    STRATEGIES,
    min_max_normalize,
    normalization_warnings,
    normalize,
)
from .pairwise import (
    PairSuperiority,
    PairwiseSuperiorityReport,
    pairwise_superiority,
)
from .perturbation import (
    PairPerturbation,
    WeightPerturbationReport,
    smallest_weight_perturbation,
)
from .promethee import promethee_ii
from .rank_sensitivity import (
    RankSensitivityReport,
    ToolRankSensitivity,
    rank_sensitivity,
)
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
from .specification_curve import (
    Specification,
    SpecificationCurveReport,
    specification_curve,
)
from .topsis import topsis
from .transitivity import PairwiseTransitivityReport, pairwise_transitivity
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
    "AttributionReport",
    "AttributionSetting",
    "BayesianSignReport",
    "CardDataConsistencyReport",
    "ConsistencyFinding",
    "CriticalDifferenceReport",
    "DatasetConcordanceReport",
    "DatasetDiscriminationReport",
    "DatasetSensitivityReport",
    "DifficultyConcordanceReport",
    "IncompatibleScaleError",
    "IncompleteMatrixError",
    "InconsistentPairwiseMatrixError",
    "MetricBaseline",
    "MetricConsistency",
    "MetricDiagnosticsReport",
    "MetricDimensionalityReport",
    "MetricReliabilityReport",
    "MetricValidityReport",
    "NoiseFloorReport",
    "NormalizationAgreementReport",
    "PairPerturbation",
    "PairPosterior",
    "PairSeparation",
    "PairSuperiority",
    "PairwiseSuperiorityReport",
    "PairwiseTransitivityReport",
    "RandomBaselineReport",
    "RankDeviation",
    "RankSensitivityReport",
    "RegistryContext",
    "Result",
    "SMAAReport",
    "SensitivityReport",
    "SkillingsMackReport",
    "Specification",
    "SpecificationCurveReport",
    "ToolRankSensitivity",
    "WeightPerturbationReport",
    "aggregate_across_datasets",
    "aggregation_agreement",
    "ahp_weights",
    "attribution_synthesis",
    "bayesian_sign_comparison",
    "beats_random_baseline",
    "card_data_consistency",
    "comet",
    "coverage_aware_critical_difference",
    "critic_weights",
    "critical_difference",
    "dataset_concordance",
    "dataset_discrimination",
    "difficulty_concordance",
    "entropy_weights",
    "equal_weights",
    "leave_one_dataset_out",
    "leave_one_metric_out",
    "merec_weights",
    "metric_diagnostics",
    "metric_dimensionality",
    "metric_reliability",
    "metric_validity",
    "min_max_normalize",
    "nemenyi_critical_difference",
    "noise_floor_separation",
    "normalization_agreement",
    "normalization_warnings",
    "normalize",
    "pairwise_superiority",
    "pairwise_transitivity",
    "promethee_ii",
    "rank",
    "rank_sensitivity",
    "reduce_tensor",
    "registry_context",
    "run",
    "run_from_registry",
    "setting_from_rank_sensitivity",
    "setting_from_same_data_contrast",
    "setting_from_source_variance",
    "skillings_mack",
    "smaa",
    "smallest_weight_perturbation",
    "specification_curve",
    "standard_deviation_weights",
    "topsis",
    "validate_for_aggregation",
    "vikor",
    "weighted_sum",
]
