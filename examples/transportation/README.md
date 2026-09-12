# Transportation

`transportation.qmd` runs beam on a made-up transportation example. Ten transport modes (foot, road running, trail running, bicycle, e-bike, motorcycle, train, kayak, boat, plane) are the methods and six terrains (flat road, mud, uphill, open water, long distance, urban hop) the datasets. The metrics are speed (higher is better), cost and CO2 (lower is better), with bundled metric cards. The numbers are illustrative.

No mode runs on every terrain, and the fastest mode differs between terrains.

The data and two helpers (`feasible_submatrix`, `common_feasible_block`) are in `beam.scenarios` as `transportation_benchmark()`, covered by `tests/test_scenarios.py`.

```
quarto render examples/transportation/transportation.qmd
```
