# Transportation: a cross-domain MCDA example

This folder holds a standalone vignette that runs the beam MCDA core on a made-up transportation problem instead of a bioinformatics benchmark. Transport modes (foot, road running, trail running, bicycle, e-bike, motorcycle, train, kayak, boat, plane) play the role of the methods, and terrains (flat road, mud, uphill, open water, long distance, urban hop) play the role of the datasets. Each mode is scored on a terrain by speed (higher is better), cost (lower is better), and CO2 (lower is better). The numbers are illustrative. The example does not use the metric registry: it carries its own polarity and per-metric normalization.

The point of the example is to make three facts visible that the bio scenarios state but do not show as sharply:

1. No mode is fastest on every terrain (the method-by-dataset interaction). A train leads on the flat road and the urban hop, a motorcycle on mud and uphill, a boat on open water, a plane on the long distance. A single global ranking cannot report all of these at once.
2. No mode runs on every terrain (partial coverage). Infeasible mode-terrain pairs are NaN. Because the coverage is incomplete, a single pooled ranking over all modes is not even well defined, so the honest output is per-terrain.
3. The slower modes cross over within the land terrains. Trail running is slower than road running on the flat road but faster on mud and uphill, and an e-bike is faster than a bicycle on the flat road and the urban hop but slower uphill. On the water the kayak is slower than the motorboat but cheaper and zero CO2. The mode that is faster on one terrain is slower on another, so a pooled order is wrong on at least one terrain.

`transportation.qmd` walks through:

- the speed heatmap, with infeasible cells left blank and the fastest mode per terrain marked as the ground truth;
- per-terrain MCDA on the feasible modes of each terrain, dropping NaN rows per terrain (the example-level NaN handling), showing that a different mode ranks first on different terrains once speed is weighted;
- the trail-running crossover, slower than road running on the flat road and faster on mud and uphill, read straight from the speed table as a clean case of method-by-dataset interaction;
- a comparison of all five aggregation methods (SAW, TOPSIS, VIKOR, PROMETHEE II, COMET) on the long-distance terrain, where every mode is feasible;
- a comparison of weightings (equal, entropy, std, CRITIC) on the same terrain, with a note that MEREC needs a zero-free normalization and so is run under z-score;
- a Demsar critical-difference diagram restricted to the four ground modes and the five terrains they all share;
- SMAA (TOPSIS) on the long-distance terrain, reporting the confidence factor per mode;
- a Triantaphyllou-Sanchez weight perturbation (SAW) on the long-distance terrain, reporting the most fragile pair;
- leave-one-dataset-out on the complete water block (kayak, motorboat, plane on open water and the long distance), showing that the plane ranks first only because the long leg is in the pool: drop that terrain and the motorboat ranks first on the water itself.

The data and two helpers (`feasible_submatrix`, `common_feasible_block`) live in `beam.scenarios` as `transportation_benchmark()`; they are covered by `tests/test_scenarios.py`.

## How to render

The vignette is a Quarto document. With Quarto installed and the beam package available in the active environment:

```
quarto render transportation.qmd
```

This produces a self-contained `transportation.html`. To run the Python chunks without Quarto, paste each `{python}` block into a session that has `beam` and `matplotlib` installed, in order.
