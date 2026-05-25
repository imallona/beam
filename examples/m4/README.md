# M4 forecasting competition: a large real benchmark

This folder holds a vignette that runs the beam MCDA core on the M4 forecasting competition (Makridakis, Spiliotis and Assimakopoulos 2020), a large real benchmark from outside bioinformatics. The 25 top methods play the role of the methods, the six frequency bands (yearly, quarterly, monthly, weekly, daily, hourly) play the role of the datasets, and the two error metrics sMAPE and MASE are bundled metric cards (`smape`, `mase`), both lower is better.

The example complements the Duo 2018 clustering benchmark (real, bio, mostly stable) and the transportation example (illustrative, partial coverage). M4 adds a large real non-bio benchmark with strong method-by-dataset interaction across the frequency bands.

`m4.qmd` walks through:

- the provenance of the bundled table, including the git-lfs clone of `M4comp2018` at commit `3c75dcd`, the `reduce_m4.R` reduction, and the validation that the reduction reproduces the published competition figures (the ES-RNN winner computes to overall sMAPE 11.374 and MASE 1.536);
- loading the table with `beam.datasets.load_m4` and reading the metric semantics from the `smape` and `mase` cards with `properties_for`;
- a headline MCDA run through `beam.rank`, with a note that pooling each band equally gives a different top method than the official OWA ranking weighted by series count;
- the per-band sMAPE rank heatmap, showing the same method leading on one band and trailing on another;
- leave-one-frequency-band-out rank stability, with the hourly band the most influential;
- a self-contained HTML report from `beam.report`, including a critical-difference diagram across the six bands.

## Data and reproducibility

The bundled table `src/beam/data/M4_2018_by_frequency.csv` is a small derived artefact (25 methods by 6 bands by 2 metrics). beam does not ship the 100,000 raw series. The table was computed once from the GPL-3 `M4comp2018` data by `src/beam/data/reduce_m4.R`; see `src/beam/data/README.md` for the full provenance, the metric definitions, and the license. To regenerate it:

```
git clone https://github.com/carlanetto/M4comp2018.git
cd M4comp2018 && git lfs pull
Rscript /path/to/beam/src/beam/data/reduce_m4.R
```

The loader and the metric mapping are covered by `tests/test_datasets_m4.py`.

## How to render

The vignette is a Quarto document. With Quarto installed and the beam package available:

```
quarto render m4.qmd
```

This produces a self-contained `m4.html`. To run the Python chunks without Quarto, paste each `{python}` block into a session that has `beam` and `matplotlib` installed, in order.
