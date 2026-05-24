# Duo 2018 clustering benchmark

This folder holds the walkthrough vignette for the re-analysis of the fourteen single-cell clustering methods from Duo, Robinson and Soneson (2018).

`duo2018.qmd` runs on the real published data, loaded with `beam.datasets.load_duo2018` (the bundled `DuoSCClustering2018.csv`, provenance in `src/beam/data/README.md`). The vignette loads the 14 methods by 12 datasets by 4 metrics tensor and reports the missing cells. It pulls the metric cards for ARI, runtime and Shannon entropy difference, then pools each metric across the twelve datasets with the rule its card recommends (NaN-aware, at the example level). It runs `run_from_registry`, compares rankings across four weightings crossed with four aggregation methods, and draws a Demsar critical-difference diagram on ARI. It reports SMAA confidence and a smallest-weight-perturbation check, and closes with a recommendation paragraph that reports what the data show.

Cluster-count deviation is left out of the pooled analysis: 101 of its 168 cells are missing, too sparse to pool without an imputation choice that would drive the result.

## Rendering

The vignette is a Quarto document. With Quarto and the project environment available:

```
quarto render examples/duo2018/duo2018.qmd
```

If Quarto is not installed, every Python chunk can be extracted and run directly with the project interpreter to confirm it executes, for example:

```
python - <<'PY'
import re, pathlib
text = pathlib.Path("examples/duo2018/duo2018.qmd").read_text()
chunks = re.findall(r"```\{python\}\n(.*?)```", text, re.DOTALL)
exec(compile("\n".join(chunks), "duo2018_chunks", "exec"))
PY
```

## Regression test

`tests/test_duo_regression.py` pins this computation. It rebuilds the pooled, normalized 14 by 3 matrix exactly as the vignette does. It then asserts that beam's induced ranking matches pymcdm for saw, topsis, vikor and promethee_ii, that the pooled matrix carries no NaN, and that the top-ranked method under the default pipeline is stable across weightings. Run it with:

```
python -m pytest tests/test_duo_regression.py -q
```
