# Bundled data

## DuoSCClustering2018.csv

A method by metric result matrix from the single-cell RNA-seq clustering benchmark of Duo, Robinson and Soneson (2018).

### Provenance

Duo A, Robinson MD, Soneson C. A systematic performance evaluation of clustering methods for single-cell RNA-seq data. F1000Research 2018, 7:1141. DOI 10.12688/f1000research.15666.3.

The underlying clustering results and data sets are distributed in the DuoClustering2018 Bioconductor experiment-data package (https://bioconductor.org/packages/DuoClustering2018), maintained by Angelo Duo and Charlotte Soneson, and in Charlotte Soneson's bettr deployment of the same benchmark. This CSV is the wide method by metric table used by that bettr app.

### Shape

14 methods (rows) by 12 data sets by 4 metrics. The first column holds the method name. The remaining 48 columns are named `<metric>_<dataset>`.

Methods: CIDR, FlowSOM, monocle, PCAHC, PCAKmeans, pcaReduce, RaceID2, RtsneKmeans, SAFE, SC3, SC3svm, Seurat, TSCAN, ascend.

Data sets: Koh, KohTCC, Kumar, KumarTCC, SimKumar4easy, SimKumar4hard, SimKumar8hard, Trapnell, TrapnellTCC, Zhengmix4eq, Zhengmix4uneq, Zhengmix8eq.

Metric column prefixes and the beam metric ids they map to:

- `ARI` maps to `ari`, the adjusted Rand index against the reference labels, higher is better.
- `elapsed` maps to `runtime`, wall-clock seconds, lower is better.
- `s.norm.vs.true` maps to `shannon_entropy_diff`, the difference in normalized Shannon entropy of the cluster size distribution between the estimated and the true partition, lower is better.
- `nclust.vs.true` maps to `nclust_deviation`, the deviation of the estimated number of clusters from the true number, lower is better.

### Missing values

Missing cells are the literal string `NA`. The counts are 5 in `ARI`, 5 in `elapsed`, 5 in `s.norm.vs.true`, and 101 in `nclust.vs.true` (the cluster-count column is sparsely populated because not every method reports a fixed cluster count for every data set). The loader in `beam.datasets` reads these as `numpy.nan` and does not impute or drop them.

### License

The Duo 2018 article is open access under CC-BY 4.0. The DuoClustering2018 Bioconductor package is released under GPL (>= 2), as listed on its Bioconductor landing page. This bundled CSV is redistributed under those terms; cite Duo, Robinson and Soneson (2018) when using it.

## M4_2018_by_frequency.csv

A method by frequency by metric results table derived from the M4 forecasting competition (Makridakis, Spiliotis and Assimakopoulos 2020).

### Shape

25 methods (the top 25 by competition OWA rank, in rank order) by 6 frequency bands (Yearly, Quarterly, Monthly, Weekly, Daily, Hourly) by 2 metrics. The long CSV has one row per method and band with columns `method, frequency, smape, mase, n_series`. The two metrics map to the bundled registry as `smape` and `mase`, both lower is better.

### How it was generated

beam does not ship the 100,000 raw series, only this small derived table. It was computed once from the GPL-3 `M4comp2018` R package, which carries the realized future values and the point forecasts of the top 25 methods. The reduction script is `reduce_m4.R` in this folder. The exact steps:

```
git clone https://github.com/carlanetto/M4comp2018.git
cd M4comp2018 && git lfs pull          # M4.rda is stored via git-lfs
# source commit 3c75dcd25c72c631f04bff1a017d9917d0e7251c, R 4.3.3
Rscript reduce_m4.R                    # writes M4_2018_by_frequency.csv
```

`reduce_m4.R` computes, per method per band, the mean sMAPE and mean MASE over the series in that band. sMAPE uses the M4 symmetric definition `2*|F-A|/(|F|+|A|)` averaged over the horizon, in percent. MASE scales the mean absolute error by the in-sample seasonal naive error, with seasonal period `m` = 1 for Yearly, Weekly and Daily, 4 for Quarterly, 12 for Monthly, 24 for Hourly. Method labels come from `submission_info` (the author surname; benchmark rows keep their names such as Theta, ARIMA, ETS).

### Reproducibility check

The reduction reproduces the published competition figures: the winner (Smyl, the ES-RNN) computes to an overall sMAPE of 11.374 and MASE of 1.536, which matches the M4 paper. The numeric reproduction is shown in the M4 vignette; the loader is covered by `tests/test_datasets_m4.py`.

### Note on pooling

The official M4 ranking pools by OWA over all 100,000 series, so it is weighted by series count and dominated by the monthly and yearly bands. beam treats each band as one dataset and weights them equally by default, which can put a different method first. This is a deliberate, recorded choice, not a discrepancy in the data.

### License

`M4comp2018` is GPL-3. This table is derived from that GPL-3 data and is redistributed under the same terms. The unlicensed M4 results spreadsheet in the `Mcompetitions/M4-methods` repository was not used. Cite Makridakis, Spiliotis and Assimakopoulos (2020), The M4 Competition: 100,000 time series and 61 forecasting methods, International Journal of Forecasting, DOI 10.1016/j.ijforecast.2019.04.014.
