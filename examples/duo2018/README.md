# Duo 2018 clustering benchmark

`duo2018.qmd` re-analyses the fourteen single-cell clustering methods of Duo, Robinson and Soneson (2018) on twelve datasets, with ARI, runtime and Shannon entropy difference. The data are bundled (`beam.datasets.load_duo2018`, provenance in `src/beam/data/README.md`).

```
quarto render examples/duo2018/duo2018.qmd
```

`tests/test_duo_regression.py` checks the pooled matrix and the rankings against pymcdm:

```
python -m pytest tests/test_duo_regression.py -q
```
