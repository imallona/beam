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
primitive (normalization, weighting, aggregation, SMAA, leave-one-metric-out,
Triantaphyllou-Sanchez) flips a documented assertion.

Kinds covered:

- ``no_signal``: every score is drawn iid. No method should consistently
  come out on top; SMAA confidence factors stay near 1 / n_tools; the
  smallest weight perturbation is small for every pair.
- ``dominant``: one method dominates on every metric. Its rank is
  1 under any weighting; SMAA confidence factor for the top-performing
  method is 1; no single-criterion weight perturbation can move it off the
  top rank.
- ``ties``: two methods produce identical score vectors. They share
  their rank under any weighting.
- ``odd_dataset``: one method is best on most datasets, another is best on
  one odd dataset. The cross-dataset aggregation rule from each metric
  card determines the top-performing method overall; the odd-dataset
  signal is visible only when the per-dataset tensor is inspected directly.

Two further scenarios expose where plain min-max scaling goes wrong, and
why the card chooses a different normalization. They are returned by
``normalization_failure_scenarios`` rather than by ``all_scenarios``, and
each is built so the top-ranked method under unguarded all-min_max differs
from the top-ranked method under the card defaults:

- ``minmax_heavy_tail``: one runtime outlier sets the min-max scale and
  hides the real speed differences among the good methods. ``log_min_max``
  keeps them.
- ``minmax_chance_baseline``: min-max maps a chance-level ARI to the
  column midpoint, so a no-better-than-random method outranks a modestly
  better one. ``baseline_relative`` maps chance to 0 and restores order.
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
    "no method that reliably comes out on top" the expectation states a
    bound, not an exact value, so the test suite can run with a tractable
    number of SMAA samples without flaking.
    """

    expected_top_ranked: int | None
    smaa_top_confidence_atleast: float | None
    smaa_top_confidence_atmost: float | None
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
    Pareto-dominant, so which method comes out on top depends entirely on
    the choice of weights. SMAA confidence is spread across the Pareto
    frontier rather than concentrated on one method.
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
            expected_top_ranked=None,
            smaa_top_confidence_atleast=None,
            smaa_top_confidence_atmost=0.8,
            top_rank_is_fragile_expected=True,
            tied_pair=None,
        ),
        seed=seed,
    )


def dominant_method_scenario(
    n_tools: int = 5,
    top: int = 0,
    seed: int = 0,
) -> Scenario:
    """One method dominates on every metric.

    The chosen method's ARI is set above every other tool's draw, and its
    runtime below. Under any positive weighting it ranks first and SMAA's
    confidence factor for it is 1.
    """
    rng = np.random.default_rng(seed)
    ari = rng.uniform(0.05, 0.35, size=n_tools)
    runtime = rng.lognormal(mean=np.log(120.0), sigma=0.2, size=n_tools)
    ari[top] = 0.9
    runtime[top] = 20.0
    scores = np.column_stack([ari, runtime])
    return Scenario(
        name="dominant",
        kind="dominant",
        description=(
            f"Method {top} dominates on every metric. Under any positive "
            "weighting it ranks first; no single-criterion weight "
            "perturbation can move it off the top rank."
        ),
        method_names=tuple(f"m{i}" for i in range(n_tools)),
        metric_ids=("ari", "runtime"),
        scores=scores,
        scores_per_dataset=None,
        expectation=ScenarioExpectation(
            expected_top_ranked=top,
            smaa_top_confidence_atleast=1.0,
            smaa_top_confidence_atmost=None,
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
            expected_top_ranked=None,
            smaa_top_confidence_atleast=None,
            smaa_top_confidence_atmost=None,
            top_rank_is_fragile_expected=None,
            tied_pair=tied_pair,
        ),
        seed=seed,
    )


def odd_dataset_scenario(
    n_tools: int = 4,
    n_datasets: int = 5,
    global_top: int = 0,
    odd_dataset_top: int = 1,
    seed: int = 0,
) -> Scenario:
    """One method best overall, with one odd dataset.

    Method ``global_top`` is best on every dataset except the last,
    where it does poorly. Method ``odd_dataset_top`` is best on that
    last dataset. The cross-dataset aggregation rule declared on the
    metric cards determines the pooled ranking from the per-dataset scores.
    """
    rng = np.random.default_rng(seed)
    n_metrics = 2
    tensor = np.zeros((n_tools, n_datasets, n_metrics))
    for d in range(n_datasets):
        ari = rng.uniform(0.05, 0.35, size=n_tools)
        runtime = rng.lognormal(mean=np.log(80.0), sigma=0.2, size=n_tools)
        if d < n_datasets - 1:
            ari[global_top] = 0.7 + rng.uniform(0, 0.1)
            runtime[global_top] = 25.0
        else:
            ari[odd_dataset_top] = 0.75
            runtime[odd_dataset_top] = 22.0
            ari[global_top] = 0.0
            runtime[global_top] = 220.0
        tensor[:, d, 0] = ari
        tensor[:, d, 1] = runtime

    metric_ids = ("ari", "runtime")
    pooled = _pool_with_recommended_rules(tensor, metric_ids)
    return Scenario(
        name="odd_dataset",
        kind="odd_dataset",
        description=(
            f"Method {global_top} is best on {n_datasets - 1} out of "
            f"{n_datasets} datasets; method {odd_dataset_top} is best on the "
            "last (odd) dataset. After cross-dataset aggregation with the "
            "per-metric recommended rule, the pooled ranking still has "
            f"method {global_top} first."
        ),
        method_names=tuple(f"m{i}" for i in range(n_tools)),
        metric_ids=metric_ids,
        scores=pooled,
        scores_per_dataset=tensor,
        expectation=ScenarioExpectation(
            expected_top_ranked=global_top,
            smaa_top_confidence_atleast=0.5,
            smaa_top_confidence_atmost=None,
            top_rank_is_fragile_expected=None,
            tied_pair=None,
        ),
        seed=seed,
    )


def outlier_runtime_scenario(seed: int = 0) -> Scenario:
    """A runtime outlier breaks unguarded min-max scaling.

    Four methods of comparable accuracy sit on a clean runtime ladder of
    10, 20, 40 and 80 seconds. A fifth method is a 5000 second outlier.
    Plain min-max anchors the runtime scale on that outlier, so the four
    good methods all map to about 0.99 and their real speed differences
    disappear. A tiny ARI difference then decides the order, and the
    slightly more accurate but twice as slow method m1 comes out on top.
    The card default log_min_max keeps the multiplicative ladder, so the
    genuinely fastest good method m0 ranks first instead. The two pipelines
    put different methods on top.
    """
    ari = np.array([0.50, 0.55, 0.49, 0.50, 0.50])
    runtime = np.array([10.0, 20.0, 40.0, 80.0, 5000.0])
    scores = np.column_stack([ari, runtime])
    return Scenario(
        name="outlier_runtime",
        kind="minmax_heavy_tail",
        description=(
            "Five methods, metrics ari and runtime. Methods m0 to m3 sit on a "
            "10, 20, 40, 80 second ladder; m4 is a 5000 second outlier. Under "
            "unguarded all-min_max the outlier compresses the good methods to "
            "near 0.99 on runtime, so a tiny ARI difference decides the order "
            "and m1 comes out on top. Under the card default log_min_max the "
            "runtime ladder survives and m0 ranks first."
        ),
        method_names=tuple(f"m{i}" for i in range(5)),
        metric_ids=("ari", "runtime"),
        scores=scores,
        scores_per_dataset=None,
        expectation=ScenarioExpectation(
            expected_top_ranked=0,
            smaa_top_confidence_atleast=None,
            smaa_top_confidence_atmost=None,
            top_rank_is_fragile_expected=None,
            tied_pair=None,
        ),
        seed=seed,
    )


def chance_baseline_scenario(seed: int = 0) -> Scenario:
    """A chance-level method looks average under unguarded min-max.

    ARI is corrected for chance, so 0 means no better than random. Plain
    min-max against the declared range maps that 0 to 0.5, half way to the
    best possible score. With a second metric in play this lets a
    chance-level method outrank a genuinely better one. Here m0 is at
    chance on ARI but reasonably fast, m1 is modestly better than chance
    but slower, and m2 is the strong all-round method. Under unguarded
    all-min_max the chance method m0 ranks above m1. The card default
    baseline_relative maps chance to 0 and restores the order, m1 above
    m0. m2 ranks first under both pipelines.
    """
    ari = np.array([0.0, 0.20, 0.30])
    runtime = np.array([80.0, 100.0, 10.0])
    scores = np.column_stack([ari, runtime])
    return Scenario(
        name="chance_baseline",
        kind="minmax_chance_baseline",
        description=(
            "Three methods, metrics ari and runtime. m0 is at chance (ARI 0), "
            "m1 is modestly better (ARI 0.20) but slower, m2 is strong overall. "
            "Unguarded min-max scores the chance ARI as 0.5 and ranks m0 above "
            "m1. The card default baseline_relative scores chance as 0 and "
            "ranks m1 above m0. m2 ranks first either way."
        ),
        method_names=("m0", "m1", "m2"),
        metric_ids=("ari", "runtime"),
        scores=scores,
        scores_per_dataset=None,
        expectation=ScenarioExpectation(
            expected_top_ranked=2,
            smaa_top_confidence_atleast=None,
            smaa_top_confidence_atmost=None,
            top_rank_is_fragile_expected=None,
            tied_pair=None,
        ),
        seed=seed,
    )


_ALL_GENERATORS = (
    random_scenario,
    dominant_method_scenario,
    tied_scenario,
    odd_dataset_scenario,
)

_NORMALIZATION_FAILURE_GENERATORS = (
    outlier_runtime_scenario,
    chance_baseline_scenario,
)


def all_scenarios(seed: int = 0) -> list[Scenario]:
    """Return one instance of every canonical scenario, all with the same seed.

    Useful for the test suite and for the scenarios vignette so each
    generator is exercised with documented inputs in one call.
    """
    return [gen(seed=seed) for gen in _ALL_GENERATORS]


def normalization_failure_scenarios(seed: int = 0) -> list[Scenario]:
    """Return the scenarios that expose the failure modes of plain min-max.

    Each one is built so the top-ranked method under unguarded all-min_max
    differs from the one under the card defaults. They drive the normalization
    section of the scenarios vignette and the regression tests that pin
    the contrast between strategies.
    """
    return [gen(seed=seed) for gen in _NORMALIZATION_FAILURE_GENERATORS]
