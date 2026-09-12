# M4 forecasting competition

`m4.qmd` ranks the 25 top methods of the M4 forecasting competition (Makridakis, Spiliotis and Assimakopoulos 2020) over six frequency bands (yearly, quarterly, monthly, weekly, daily, hourly) with sMAPE and MASE, both lower is better.

```
quarto render examples/m4/m4.qmd
```

## Data

`src/beam/data/M4_2018_by_frequency.csv` has 25 methods by 6 bands by 2 metrics, computed from the GPL-3 `M4comp2018` data by `src/beam/data/reduce_m4.R`; see `src/beam/data/README.md`. To reproduce, run:

```
git clone https://github.com/carlanetto/M4comp2018.git
cd M4comp2018 && git lfs pull
Rscript /path/to/beam/src/beam/data/reduce_m4.R
```

`tests/test_datasets_m4.py` covers the loader.
