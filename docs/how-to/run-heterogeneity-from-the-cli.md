# Run a heterogeneity model from the command line

Use this recipe when the MCDA ranking pools several datasets and you want to know whether one method is really ahead or whether the order depends on which datasets are in the pool. The `beam heterogeneity` command fits one of the method-dataset heterogeneity models on a score file and writes the report as JSON.

These models wrap R, so the command needs the R toolchain. The conda recipe `envs/heterogeneity.yml` installs Python and R together with the packages each model uses. When a package is missing the command stops with a clear error naming it, so a script can branch on the exit code (0 on success, 2 on any error).

## The input

The score file is long format: a header `tool,dataset,metric,score` and one row per measurement. The dataset column is what these models decompose, so a wide tool by metric file is rejected. When the file holds more than one metric, pick one with `--metric`.

```
beam heterogeneity scores.csv --model mixed-effects --metric ari --out report.json
```

## The three models

`mixed-effects` fits `score ~ method + (1 | dataset)` in lme4 and splits the score variation into a method effect, a between-dataset shift, and the residual. The report carries the variance components, the dataset ICC (the share of variation that is the dataset rather than the method), and the per-method marginal means. A high ICC means most of the spread is between datasets, so a single pooled ranking hides much of the structure.

`bradley-terry-tree` fits a Bradley-Terry tree in psychotree. It splits the datasets by their features so each leaf has its own method ranking, and flags the leaves where the pooled top method does not hold. It needs a dataset features file, passed with `--features`:

```
beam heterogeneity scores.csv --model bradley-terry-tree --metric ari \
    --features dataset_features.csv --out tree.json
```

The features file has a header whose first column is the dataset id and whose other columns are the features. A column whose values all parse as numbers becomes a numeric split candidate; the rest are treated as categorical. Every dataset in the score file must have a row.

```
dataset,n_cells,n_clusters,kind
d1,531,9,real
d2,3994,3,sim
```

`plackett-luce` fits a Plackett-Luce model in PlackettLuce on the per-dataset rankings of the methods, and reports the worth per method with quasi-standard errors. It is the full-ranking generalization of the Bradley-Terry model and needs no features.

## The output

Without `--out` the report prints to stdout as JSON. With `--out` the JSON goes to the file and a one-line summary prints to stdout, for example:

```
ok: mixed-effects on ari, the between-dataset shift is 0.71 of the variance
```

The JSON is the same report object the Python API returns, so a downstream script reads the variance components, the tree nodes and per-leaf worths, or the Plackett-Luce ranking without re-running the fit.

## What it does not do

The command fits the model and serializes the report. It does not draw the tree or render an HTML page; for the worth panel inside the funky heatmap, run the Python API and pass the worth into `funky_heatmap_from_run`. The cross-benchmark `source_variance_decomposition` model takes a different input shape (scores labelled by benchmark) and is not exposed here; call it from Python.
