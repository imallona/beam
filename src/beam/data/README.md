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
