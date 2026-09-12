# Canonical simulated scenarios

`scenarios.qmd` runs the pipeline on four simulated benchmarks from `beam.scenarios` with a known result:

- `random`: ARI and runtime are anti-correlated, so no method scores higher on both and the top method depends on the weighting.
- `dominant`: one method scores highest on every metric and ranks first under any weighting.
- `ties`: two methods have identical scores and share a rank.
- `odd_dataset`: one method ranks first on most datasets and another on one dataset.

Each generator returns a `Scenario` with the pooled tool by metric matrix, the optional per-dataset tensor, the metric ids, and a `ScenarioExpectation`. `tests/test_scenarios.py` checks the pipeline against them.

```
quarto render examples/scenarios/scenarios.qmd
```
