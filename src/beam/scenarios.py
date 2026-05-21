"""Canonical simulated benchmark scenarios with known ground truth.

Every generator returns a ``Scenario`` carrying a tool by metric score
matrix (and, when relevant, the underlying tool by dataset by metric
tensor it was reduced from), the metric ids used, and a label for the
kind of ground truth the scenario was built to encode. The accompanying
``ScenarioExpectation`` documents what the MCDA pipeline and the
sensitivity primitives ought to say about it.

The scenarios sit underneath the MCDA module. Their purpose is to give
the test suite and the documentation a controlled set of inputs whose
correct interpretation is known up front, so a regression in any single
primitive (normalisation, weighting, aggregation, SMAA, leave-one-metric-out,
Triantaphyllou-Sanchez) flips a documented assertion.

Kinds covered:

- ``no_signal``: every score is drawn iid. No method should win
  reliably; SMAA confidence factors stay near 1 / n_tools; the smallest
  weight perturbation is small for every pair.
- ``clear_winner``: one method dominates on every metric. Its rank is
  1 under any weighting; SMAA confidence factor for the winner is 1;
  no single-criterion weight perturbation can dethrone it.
- ``ties``: two methods produce identical score vectors. They share
  their rank under any weighting.
- ``odd_dataset``: one method wins on most datasets, another wins on
  one odd dataset. The cross-dataset aggregation rule from each metric
  card determines the global winner; the odd-dataset signal is visible
  only when the per-dataset tensor is inspected directly.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .cards import properties_for
from .mcda import aggregate_across_datasets


@dataclass(frozen=True)
class ScenarioExpectation:
    """What the MCDA pipeline ought to report about a scenario.

    Fields are deliberately conservative: where the ground truth is
    "no real winner" the expectation states a bound, not an exact
    value, so the test suite can run with a tractable number of SMAA
    samples without flaking.
    """

    expected_winner: int | None
    smaa_winner_confidence_atleast: float | None
    smaa_winner_confidence_atmost: float | None
    top_rank_is_fragile_expected: bool | None
    tied_pair: tuple[int, int] | None


@dataclass(frozen=True)
class Scenario:
    """A single benchmark instance with documented ground truth.

    ``scores`` is the pooled tool by metric matrix consumed by
    ``beam.mcda.run_from_registry``. ``scores_per_dataset`` is the
    tool by dataset by metric tensor it was reduced from, or ``None``
    for single-dataset scenarios. ``metric_ids`` matches the column
    order of ``scores`` and corresponds to ids in the bundled metric
    registry.
    """

    name: str
    kind: str
    description: str
    method_names: tuple[str, ...]
    metric_ids: tuple[str, ...]
    scores: np.ndarray
    scores_per_dataset: np.ndarray | None
    expectation: ScenarioExpectation
    seed: int


def _pool_with_recommended_rules(
    tensor: np.ndarray,
    metric_ids: tuple[str, ...],
) -> np.ndarray:
    """Reduce a (n_tools, n_datasets, n_metrics) tensor to (n_tools, n_metrics).

    Each metric column is folded over the dataset axis using the rule
    declared on its card (arithmetic_mean, geometric_mean, median,
    rank_mean). When no rule is declared the function falls back to
    arithmetic mean.
    """
    props = properties_for(list(metric_ids))
    cols = []
    for k, p in enumerate(props):
        rule = p.recommended_aggregation_across_datasets or "arithmetic_mean"
        cols.append(aggregate_across_datasets(tensor[:, :, k], rule=rule))
    return np.column_stack(cols)


def random_scenario(n_tools: int = 5, seed: int = 0) -> Scenario:
    """No-signal scenario with trade-offs enforced.

    ARI and runtime are drawn from the same iid distributions as in the
    other scenarios, then re-paired so high-ARI methods also take higher
    runtime. The anti-correlation guarantees that no single method is
    Pareto-dominant, so the winner depends entirely on the choice of
    weights. SMAA confidence is spread across the Pareto frontier rather
    than concentrated on one method.
    """
    rng = np.random.default_rng(seed)
    ari = np.sort(rng.uniform(0.05, 0.55, size=n_tools))
    runtime = np.sort(rng.lognormal(mean=np.log(60.0), sigma=0.4, size=n_tools))
    # high-ARI methods inherit high runtime; this is the trade-off.
    scores = np.column_stack([ari, runtime])
    # shuffle method index so the trade-off is not aligned with method ordering
    permutation = rng.permutation(n_tools)
    scores = scores[permutation]
    return Scenario(
        name="random",
        kind="no_signal",
        description=(
            "ARI and runtime are drawn iid then re-paired so the two metrics "
            "are anti-correlated. No method Pareto-dominates the rest; the "
            "ranking depends entirely on the weighting. SMAA confidence is "
            "spread across the Pareto-frontier methods rather than "
            "concentrated on one."
        ),
        method_names=tuple(f"m{i}" for i in range(n_tools)),
        metric_ids=("ari", "runtime"),
        scores=scores,
        scores_per_dataset=None,
        expectation=ScenarioExpectation(
            expected_winner=None,
            smaa_winner_confidence_atleast=None,
            smaa_winner_confidence_atmost=0.8,
            top_rank_is_fragile_expected=True,
            tied_pair=None,
        ),
        seed=seed,
    )


def clear_winner_scenario(
    n_tools: int = 5,
    winner: int = 0,
    seed: int = 0,
) -> Scenario:
    """One method dominates on every metric.

    The winner's ARI is set above every other tool's draw; its runtime
    is set below every other tool's draw. Under any positive weighting
    the winner is rank 1 and SMAA's confidence factor for it is 1.
    """
    rng = np.random.default_rng(seed)
    ari = rng.uniform(0.05, 0.35, size=n_tools)
    runtime = rng.lognormal(mean=np.log(120.0), sigma=0.2, size=n_tools)
    ari[winner] = 0.9
    runtime[winner] = 20.0
    scores = np.column_stack([ari, runtime])
    return Scenario(
        name="clear_winner",
        kind="clear_winner",
        description=(
            f"Method {winner} dominates on every metric. Under any positive "
            "weighting it is ranked first; no single-criterion weight "
            "perturbation can dethrone it."
        ),
        method_names=tuple(f"m{i}" for i in range(n_tools)),
        metric_ids=("ari", "runtime"),
        scores=scores,
        scores_per_dataset=None,
        expectation=ScenarioExpectation(
            expected_winner=winner,
            smaa_winner_confidence_atleast=1.0,
            smaa_winner_confidence_atmost=None,
            top_rank_is_fragile_expected=False,
            tied_pair=None,
        ),
        seed=seed,
    )


def tied_scenario(
    n_tools: int = 5,
    tied_pair: tuple[int, int] = (0, 1),
    seed: int = 0,
) -> Scenario:
    """Two methods produce identical scores; the rest are noisy.

    The tied pair shares its rank under any weighting. The expectation
    flags this so the test suite can check rank equality and SMAA
    rank-acceptability equality for the pair.
    """
    rng = np.random.default_rng(seed)
    ari = rng.uniform(0.05, 0.55, size=n_tools)
    runtime = rng.lognormal(mean=np.log(60.0), sigma=0.4, size=n_tools)
    a, b = tied_pair
    ari[b] = ari[a]
    runtime[b] = runtime[a]
    scores = np.column_stack([ari, runtime])
    return Scenario(
        name="ties",
        kind="ties",
        description=(
            f"Methods {a} and {b} produce identical scores on every metric. "
            "They share a rank under any weighting."
        ),
        method_names=tuple(f"m{i}" for i in range(n_tools)),
        metric_ids=("ari", "runtime"),
        scores=scores,
        scores_per_dataset=None,
        expectation=ScenarioExpectation(
            expected_winner=None,
            smaa_winner_confidence_atleast=None,
            smaa_winner_confidence_atmost=None,
            top_rank_is_fragile_expected=None,
            tied_pair=tied_pair,
        ),
        seed=seed,
    )


def odd_dataset_scenario(
    n_tools: int = 4,
    n_datasets: int = 5,
    global_winner: int = 0,
    odd_dataset_winner: int = 1,
    seed: int = 0,
) -> Scenario:
    """A global winner with one odd dataset.

    Method ``global_winner`` wins on every dataset except the last,
    where it does poorly. Method ``odd_dataset_winner`` wins on that
    last dataset. The cross-dataset aggregation rule declared on the
    metric cards determines the global ranking from the pooled scores.
    """
    rng = np.random.default_rng(seed)
    n_metrics = 2
    tensor = np.zeros((n_tools, n_datasets, n_metrics))
    for d in range(n_datasets):
        ari = rng.uniform(0.05, 0.35, size=n_tools)
        runtime = rng.lognormal(mean=np.log(80.0), sigma=0.2, size=n_tools)
        if d < n_datasets - 1:
            ari[global_winner] = 0.7 + rng.uniform(0, 0.1)
            runtime[global_winner] = 25.0
        else:
            ari[odd_dataset_winner] = 0.75
            runtime[odd_dataset_winner] = 22.0
            ari[global_winner] = 0.0
            runtime[global_winner] = 220.0
        tensor[:, d, 0] = ari
        tensor[:, d, 1] = runtime

    metric_ids = ("ari", "runtime")
    pooled = _pool_with_recommended_rules(tensor, metric_ids)
    return Scenario(
        name="odd_dataset",
        kind="odd_dataset",
        description=(
            f"Method {global_winner} wins on {n_datasets - 1} out of "
            f"{n_datasets} datasets; method {odd_dataset_winner} wins on the "
            "last (odd) dataset. After cross-dataset aggregation with the "
            "per-metric recommended rule, the pooled ranking still has "
            f"method {global_winner} first."
        ),
        method_names=tuple(f"m{i}" for i in range(n_tools)),
        metric_ids=metric_ids,
        scores=pooled,
        scores_per_dataset=tensor,
        expectation=ScenarioExpectation(
            expected_winner=global_winner,
            smaa_winner_confidence_atleast=0.5,
            smaa_winner_confidence_atmost=None,
            top_rank_is_fragile_expected=None,
            tied_pair=None,
        ),
        seed=seed,
    )


_ALL_GENERATORS = (
    random_scenario,
    clear_winner_scenario,
    tied_scenario,
    odd_dataset_scenario,
)


def all_scenarios(seed: int = 0) -> list[Scenario]:
    """Return one instance of every canonical scenario, all with the same seed.

    Useful for the test suite and for the scenarios vignette so each
    generator is exercised with documented inputs in one call.
    """
    return [gen(seed=seed) for gen in _ALL_GENERATORS]
