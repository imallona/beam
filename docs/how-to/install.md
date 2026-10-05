# Install beam

## Python

beam is not on PyPI yet; it installs from a clone into a virtual environment:

```sh
git clone https://github.com/imallona/beam.git
python -m venv .venv
source .venv/bin/activate
pip install ./beam
```

Python 3.12 or newer.

## R

The R package is `rbeam`, installed from the checkout:

```r
devtools::install_local("beam/r/beam")
rbeam::install_beam_python()
```

`rbeam::install_beam_python()` installs the Python beam into the active reticulate environment; alternatively, reticulate uses an existing one via `reticulate::use_python()` or `RETICULATE_PYTHON`. `dependencies = TRUE` fails here: `PlackettLuce` depends on `CVXR` and `clarabel`, which need a Rust toolchain.

## Heterogeneity models

The R-backed models (mixed-effects, Bradley-Terry trees, Plackett-Luce, variance decomposition, network meta-analysis) need their own R packages, installed either from R:

```r
install_beam_heterogeneity_deps()
```

or from the conda env, which has them as binaries:

```sh
conda env create -f beam/envs/heterogeneity.yml
```
