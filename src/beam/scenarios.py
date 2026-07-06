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

from collections.abc import Sequence
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

    Each metric column is reduced over the datasets using the rule
    declared on its card (arithmetic_mean, geometric_mean, median,
    rank_mean). When no rule is declared the function uses the
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
    """Two methods are tied for first; the rest are weaker and noisy.

    The tied pair shares identical scores, set above the other methods on
    both metrics, so the pair ties for the top rank under any weighting.
    Making the pair the best methods keeps the SMAA confidence factor on
    the pair rather than on some unrelated method, so the tie is the story
    the plot tells. The expectation flags the pair so the test suite can
    check rank equality and SMAA rank-acceptability equality.
    """
    rng = np.random.default_rng(seed)
    ari = rng.uniform(0.05, 0.55, size=n_tools)
    runtime = rng.lognormal(mean=np.log(60.0), sigma=0.4, size=n_tools)
    a, b = tied_pair
    # set the pair to dominate on both metrics, identical to each other
    ari[a] = ari[b] = 0.9
    runtime[a] = runtime[b] = 15.0
    scores = np.column_stack([ari, runtime])
    return Scenario(
        name="ties",
        kind="ties",
        description=(
            f"Methods {a} and {b} have identical scores, set above the rest on "
            "both metrics, so they tie for the top rank under any weighting."
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
    generator is run with documented inputs in one call.
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


@dataclass(frozen=True)
class TransportationBenchmark:
    """A cross-domain MCDA example: transport modes scored across terrains.

    The methods are transport modes and the datasets are terrains. The data
    is illustrative and made up, but the numbers are kept in a plausible
    range so the example reads sensibly. It is deliberately not a bio
    benchmark, yet it still goes through the metric registry: the metric ids
    ``speed``, ``cost`` and ``co2`` resolve to bundled cards, so polarity and
    normalization come from the ontology rather than being carried here. This
    keeps every example, bio or not, consistent in how it reads metric
    semantics.

    The point of the example is threefold. First, no mode is fastest on every
    terrain (a boat is fastest on water, a small plane on the long leg, a
    motorcycle off-road), which is the method-by-dataset interaction that a
    single global ranking hides. Second, some modes do not run on some
    terrains at all (a boat off-road, a small plane on an urban hop). Those
    cells are NaN. Because no mode is feasible on every terrain, a single
    pooled ranking over all modes is not even well defined, so the honest
    output is per-terrain. Third, the slower modes cross over within the land
    terrains: trail running is slower than road running on the flat road but
    faster on mud and uphill, and an e-bike is faster than a bicycle on the
    flat road and the urban hop but slower uphill. A pooled speed order over
    these modes reports one ranking that is wrong on at least one terrain.

    Fields:
        mode_names: the transport modes (rows).
        terrain_names: the terrains (the datasets).
        metric_names: the metric card ids ("speed", "cost", "co2").
        scores: (n_modes, n_terrains, n_metrics) with NaN where a mode cannot
            run on a terrain.

    ``polarity`` and ``normalization`` are read from the registry cards for
    ``metric_names``, so the cards are the single source of truth.
    """

    mode_names: tuple[str, ...]
    terrain_names: tuple[str, ...]
    metric_names: tuple[str, ...]
    scores: np.ndarray

    @property
    def polarity(self) -> tuple[str, ...]:
        """Per-metric polarity, read from the registry cards for ``metric_names``."""
        return tuple(p.polarity for p in properties_for(list(self.metric_names)))

    @property
    def normalization(self) -> tuple[str, ...]:
        """Per-metric normalization strategy, read from the registry cards."""
        return tuple(
            p.recommended_normalization or "min_max"
            for p in properties_for(list(self.metric_names))
        )

    def feasible(self) -> np.ndarray:
        """Boolean (n_modes, n_terrains) mask, True where the mode runs on the terrain."""
        return ~np.isnan(self.scores[:, :, 0])

    def metric(self, name: str) -> np.ndarray:
        """The (n_modes, n_terrains) slice for one metric name."""
        return self.scores[:, :, self.metric_names.index(name)]

    def feasible_submatrix(self, terrain: str) -> tuple[tuple[str, ...], np.ndarray]:
        """Return the modes feasible on one terrain and their score submatrix.

        On a given terrain only some modes run. This drops the modes whose
        cells are NaN on that terrain and returns the remaining mode names
        together with the dense ``(n_feasible_modes, n_metrics)`` score
        matrix, ready to pass to ``beam.mcda.run``. This is the per-terrain,
        example-level NaN handling the transportation vignette documents:
        instead of imputing or pooling across terrains, each terrain is
        analysed over the modes that actually run on it.

        Parameters
        ----------
        terrain
            One of ``terrain_names``.

        Returns
        -------
        tuple of (tuple of str, numpy.ndarray)
            The feasible mode names in original row order, and the
            ``(n_feasible_modes, n_metrics)`` score matrix with no NaN.

        Raises
        ------
        ValueError
            If ``terrain`` is not in ``terrain_names``.
        """
        if terrain not in self.terrain_names:
            raise ValueError(f"unknown terrain {terrain!r}; expected one of {self.terrain_names}")
        column = self.terrain_names.index(terrain)
        mask = self.feasible()[:, column]
        rows = np.nonzero(mask)[0]
        names = tuple(self.mode_names[i] for i in rows)
        submatrix = self.scores[rows, column, :]
        return names, submatrix

    def common_feasible_block(
        self,
        modes: Sequence[str],
    ) -> tuple[tuple[str, ...], np.ndarray]:
        """Return a block of modes and the terrains on which all of them run.

        A critical-difference diagram needs a complete tool by dataset table
        with no missing cells. Because no mode runs on every terrain, the
        honest way to build such a table is to restrict to a set of modes and
        keep only the terrains where every mode in the set is feasible. This
        returns those common terrain names and the ``(n_modes, n_common)``
        speed matrix for the requested modes, in the row order given.

        Parameters
        ----------
        modes
            The mode names to include in the block.

        Returns
        -------
        tuple of (tuple of str, numpy.ndarray)
            The terrain names where every requested mode is feasible, and the
            ``(len(modes), n_common_terrains)`` speed matrix for those modes
            and terrains. Speed is used because it is the metric whose ground
            truth (fastest mode per terrain) the vignette marks.

        Raises
        ------
        ValueError
            If any requested mode is unknown, or if there is no terrain on
            which all requested modes are feasible.
        """
        for mode in modes:
            if mode not in self.mode_names:
                raise ValueError(f"unknown mode {mode!r}; expected one of {self.mode_names}")
        rows = [self.mode_names.index(mode) for mode in modes]
        feasible = self.feasible()
        common = [t for t in range(len(self.terrain_names)) if all(feasible[i, t] for i in rows)]
        if not common:
            raise ValueError(f"no terrain has every mode in {tuple(modes)} feasible")
        terrains = tuple(self.terrain_names[t] for t in common)
        speed = self.metric("speed")
        block = speed[np.ix_(rows, common)]
        return terrains, block


def transportation_benchmark() -> TransportationBenchmark:
    """Build the illustrative transportation example with infeasible cells as NaN.

    Modes: on foot, road running, trail running, bicycle, e-bike, motorcycle,
    train, kayak, boat, small plane.
    Terrains: flat road, mud, steep uphill, open water, long distance, urban hop.
    Metrics: speed (km/h, higher is better), cost (per km, lower is better),
    CO2 (g per km, lower is better). The fastest mode by terrain is train on
    the flat road and the urban hop, motorcycle on mud and uphill, boat on
    open water, and a small plane on the long distance. No mode runs on every
    terrain: the boat, kayak and plane cannot use the dry land terrains, and
    the land modes cannot cross open water.

    The slower modes cross over within the land terrains. Trail running is
    slower than road running on the flat road but faster on mud and uphill,
    where off-road traction helps. An e-bike is faster than a bicycle on the
    flat road and the urban hop but slower uphill, where its weight costs it.
    On the water, the kayak is slower than the motorboat but cheaper and zero
    CO2, so it outranks the boat on cost and CO2 while it is slower on speed.
    """
    nan = np.nan
    # rows: foot, running, trail_running, bicycle, e_bike, motorcycle, train,
    #       kayak, boat, plane
    # cols: flat_road, mud, uphill, open_water, long_distance, urban_hop
    speed = np.array(
        [
            [5, 3, 2, nan, 5, 4],
            [12, 6, 4, nan, 10, 8],
            [10, 8, 6, nan, 9, 7],
            [20, 8, 6, nan, 18, 15],
            [28, 8, 4, nan, 22, 20],
            [70, 25, 30, nan, 90, 40],
            [90, nan, nan, nan, 200, 60],
            [nan, nan, nan, 6, 8, nan],
            [nan, nan, nan, 30, 40, nan],
            [nan, nan, nan, 18, 750, nan],
        ],
        dtype=float,
    )
    cost = np.array(
        [
            [0.1, 0.2, 0.3, nan, 0.1, 0.1],
            [0.1, 0.2, 0.3, nan, 0.1, 0.1],
            [0.1, 0.2, 0.3, nan, 0.1, 0.1],
            [0.2, 0.3, 0.4, nan, 0.2, 0.2],
            [0.25, 0.35, 0.45, nan, 0.25, 0.25],
            [0.6, 1.0, 1.0, nan, 0.6, 0.7],
            [0.3, nan, nan, nan, 0.25, 0.4],
            [nan, nan, nan, 0.2, 0.5, nan],
            [nan, nan, nan, 0.6, 2.5, nan],
            [nan, nan, nan, 4.0, 1.2, nan],
        ],
        dtype=float,
    )
    co2 = np.array(
        [
            [0, 0, 0, nan, 0, 0],
            [0, 0, 0, nan, 0, 0],
            [0, 0, 0, nan, 0, 0],
            [0, 0, 0, nan, 0, 0],
            [8, 10, 12, nan, 8, 8],
            [100, 150, 150, nan, 100, 110],
            [40, nan, nan, nan, 35, 45],
            [nan, nan, nan, 0, 0, nan],
            [nan, nan, nan, 120, 250, nan],
            [nan, nan, nan, 250, 180, nan],
        ],
        dtype=float,
    )
    scores = np.stack([speed, cost, co2], axis=2)
    return TransportationBenchmark(
        mode_names=(
            "foot",
            "running",
            "trail_running",
            "bicycle",
            "e_bike",
            "motorcycle",
            "train",
            "kayak",
            "boat",
            "plane",
        ),
        terrain_names=("flat_road", "mud", "uphill", "open_water", "long_distance", "urban_hop"),
        metric_names=("speed", "cost", "co2"),
        scores=scores,
    )
