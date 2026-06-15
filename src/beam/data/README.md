# Bundled data

## DuoSCClustering2018.csv

A method by metric result matrix from the single-cell RNA-seq clustering benchmark of Duo, Robinson and Soneson (2018).

### Provenance

Duo A, Robinson MD, Soneson C. A systematic performance evaluation of clustering methods for single-cell RNA-seq data. F1000Research 2018, 7:1141. DOI 10.12688/f1000research.15666.3.

The underlying clustering results and data sets are distributed in the DuoClustering2018 Bioconductor experiment-data package (https://bioconductor.org/packages/DuoClustering2018), maintained by Angelo Duo and Charlotte Soneson, and in Charlotte Soneson's bettr deployment of the same benchmark. This CSV is the wide method-by-metric table used by that bettr app.

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

## DuoSCClustering2018_features.csv

Dataset-level descriptors for the 12 Duo 2018 data sets, used as the candidate splitting variables for the Bradley-Terry tree (`beam.heterogeneity.bradley_terry_tree`, loaded by `beam.datasets.load_duo2018_features`). One row per data set with columns `dataset, n_cells, n_clusters, source_type, family, quantification`.

### Provenance of each column

- `n_cells` and `n_clusters` (number of cells and number of true subpopulations) are taken from the DuoClustering2018 package help files for each data set (https://csoneson.github.io/DuoClustering2018/reference/): Koh 531 cells and 9 subpopulations, Kumar 246 and 3, Trapnell 222 and 3 (TrapnellTCC 227 cells), the SimKumar simulations 500 cells each (4, 4 and 8 subpopulations), and the Zheng mixtures Zhengmix4eq 4000 cells and 4 types, Zhengmix4uneq 6500 and 4, Zhengmix8eq 3994 and 8. The TCC quantification variants share their base data set's cell and cluster counts except where the help file records otherwise (TrapnellTCC).
- `source_type` follows the Duo 2018 paper's own count of 9 real and 3 simulated data sets: the three SimKumar data sets are `simulated`, the rest `real`. The Zheng mixtures are real sorted cells recombined into artificial proportions; the cells are real, so they are labelled `real` to match the paper.
- `family` is the source data set (Koh, Kumar, SimKumar, Trapnell, Zhengmix), and `quantification` is `standard` or `tcc` (transcript-compatibility counts), both parsed from the data set name.

These are coarse descriptors for demonstrating the tree; the exact post-QC cell counts in the bundled `SingleCellExperiment` objects can differ slightly from these published nominal sizes. Cite Duo, Robinson and Soneson (2018) and the DuoClustering2018 package.

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

The reduction reproduces the published competition figures: the top-ranked method (Smyl, the ES-RNN) computes to an overall sMAPE of 11.374 and MASE of 1.536, which matches the M4 paper. The numeric reproduction is shown in the M4 vignette; the loader is covered by `tests/test_datasets_m4.py`.

### Note on pooling

The official M4 ranking pools by OWA over all 100,000 series, so it is weighted by series count and dominated by the monthly and yearly bands. beam treats each band as one dataset and weights them equally by default, which can put a different method first. This is a deliberate, recorded choice, not a discrepancy in the data.

### License

`M4comp2018` is GPL-3. This table is derived from that GPL-3 data and is redistributed under the same terms. The unlicensed M4 results spreadsheet in the `Mcompetitions/M4-methods` repository was not used. Cite Makridakis, Spiliotis and Assimakopoulos (2020), The M4 Competition: 100,000 time series and 61 forecasting methods, International Journal of Forecasting, DOI 10.1016/j.ijforecast.2019.04.014.

## openproblems_batch_integration.csv, openproblems_svg.csv, openproblems_svg_features.csv

Derived results tables from OpenProblems in Single-Cell Analysis (openproblems.bio), the continuous community benchmarking platform. Loaded by `beam.datasets.load_openproblems` and `beam.datasets.load_openproblems_svg_features`.

### Provenance

OpenProblems consortium. Nature Biotechnology 2025, DOI 10.1038/s41587-025-02694-w. The results are committed as JSON in the `openproblems-bio/website` GitHub repository, one directory per task under `results/<task>/data/`. These tables were derived once from a pinned commit:

```
repo:   github.com/openproblems-bio/website
commit: 76ce7f288da591b1b19c32cbfe8ce50bc3706ece
files:  results/<task>/data/{results,metric_info,dataset_info,method_info}.json
```

Two tasks are bundled:

- `openproblems_batch_integration.csv`: the batch_integration task, 19 methods (the 7 control and baseline methods such as `no_integration` and `shuffle_integration` were dropped) by 6 cellxgene-census datasets by 13 scIB metrics (Luecken et al. 2022). Long format `method_id, dataset_id, metric_id, score`, the raw `metric_values` with the source string `NA` left empty. The 13 metrics map to the bundled cards `ari`, `nmi`, `asw_batch`, `asw_label`, `cell_cycle_conservation`, `graph_connectivity`, `hvg_overlap`, `isolated_label_asw`, `isolated_label_f1`, `kbet`, `ilisi`, `clisi`, `pcr`. Coverage is uneven (some method-by-dataset cells and the `hvg_overlap` column are sparse); beam reads the gaps as NaN.
- `openproblems_svg.csv`: the spatially_variable_genes task, 14 methods (the 2 baselines `random_ranking` and `true_ranking` dropped) by 50 spatial datasets by one `correlation` metric. Same long format.
- `openproblems_svg_features.csv`: dataset-level descriptors for the 50 spatial datasets, used as the Bradley-Terry tree splitting variables. `technology` (the spatial assay: visium, merfish, slideseqv2, stereoseq, dbitseq, seqfish, starmap, slidetags, post_xenium), `organism` (human, mouse, drosophila), and `condition` (cancer or noncancer) are parsed from the `<source>/<technology>/<name>` dataset id. The platform's `dataset_info.json` carries no structured numeric features (cell counts live only in free text), so no numeric features are provided.

All scores are reported with higher is better (the platform's `maximize` flag is true for every metric here). The metric reference DOIs recorded on the cards come from the platform's `metric_info.json`. The exact fetch and reduction (curl of the four result files at the pinned commit, dropping baselines, mapping the source `NA` to empty, parsing the spatial features from the dataset id) is shown and reproduces these tables byte for byte in `examples/openproblems/openproblems.qmd`.

### License

The OpenProblems JSON data files are licensed CC-BY-4.0 (the `openproblems-bio/website` repository dual-licenses code as MIT and data and markdown as CC-BY-4.0). These derived tables are redistributed under CC-BY-4.0 with attribution; cite the OpenProblems consortium (Nature Biotechnology 2025, DOI 10.1038/s41587-025-02694-w) and, for the batch_integration metrics, Luecken et al. (Nature Methods 2022, DOI 10.1038/s41592-021-01336-8).

## Cross-benchmark single-cell integration set (scib2022_metrics.csv, tran2020_metrics.csv, tyler2023_metrics.csv, batchbench2021_metrics.csv, batchbench2021_datasets.csv, integration_published_ranks.csv)

Five single-cell integration benchmarks harmonized on the shared scIB metric family (ARI, ASW, kBET, LISI) for the five methods common to the first three (combat, harmony, fastMNN, scanorama, LIGER). Loaded by `beam.datasets.load_integration_benchmarks` and `beam.datasets.load_integration_published_ranks`. Tyler 2023 covers three of the five methods (harmony, scanorama, LIGER) and three of the four metric families (ARI, ASW, kBET); cLISI is not slotted in because the existing `LISI` column is iLISI, a different quantity from Tyler's cell-type LISI. BatchBench 2021 (the fifth source) covers four of the five methods (combat, harmony, fastMNN, scanorama; it has no LIGER) on its own two entropy metrics rather than the scIB family, so it enters on the within-benchmark rank scale alone.

### Exact source of each table

- `scib2022_metrics.csv`: raw (unscaled) per-method per-dataset scores from scIB (Luecken et al., Nature Methods 2022, DOI 10.1038/s41592-021-01336-8). Derived from the `theislab/scib-reproducibility` repository, file `data/metrics.csv` (the same values are in `visualization/data/metrics_RNA_allTasks.csv`). Takes the `unscaled` rows for the five real datasets (immune_cell_hum, immune_cell_hum_mou, lung_atlas, mouse_brain, pancreas) and the columns `ARI_cluster/label`, `ASW_label`, `kBET`, `iLISI`, with one representative integration variant per method (combat_full, harmony_embed, fastmnn_embed, scanorama_embed, liger_embed). Unscaled values are used so beam re-derives the normalization rather than inheriting scIB's. Code MIT, the article is CC-BY 4.0; cite Luecken et al. 2022.
- `tran2020_metrics.csv`: per-method per-dataset ranks from Tran et al. (Genome Biology 2020, DOI 10.1186/s13059-019-1850-9, CC-BY 4.0), Additional file 8 (`13059_2019_1850_MOESM8_ESM.xlsx`), Table S7 "Rank and rank sums", columns ARI_rank, ASW_rank, LISI_rank, kBET_rank, for the five common methods over Tran's nine non-simulation datasets. Raw scores are also available in Additional file 5 (MOESM5) Table S4; the ranks (S7) are used here. Tran's dataset identities come from Additional file 1 (`13059_2019_1850_MOESM1_ESM.xlsx`) Table S1.
- `tyler2023_metrics.csv`: per-method per-(dataset, metric) scores from Tyler, Guccione and Schadt, "Erasure of Biologically Meaningful Signal by Unsupervised scRNAseq Batch-correction Methods", bioRxiv 2021.11.15.468733 v2 (2023-10-26), preprint only (Crossref confirms no journal version, checked 2026-05-28). Extended Data Table 2 sheet A (StateObs_vs_NotObs_vals), the `observed_metric` column averaged across the two `ref_clust_method` variants (`pca_euc`, `spear_euc`), for the three methods common to Tyler and beam's set (harmony, scanorama, liger) over the two in silico runs (`MAPK_ERK_signaling_in_ALL_final_bio` and `MAPK_ERK_signaling_in_Tcell_final_bio`) and three shared metrics. The selected metric names map as: `ari_celltype` to ARI (higher is better), `asw` to ASW (higher is better), `mean_kBET_within_cell_type` to kBET (lower is better, the raw rejection rate, opposite polarity to scIB's reported kBET). The bioRxiv preprint is CC-BY-NC-ND 4.0; numerical results in a published table are facts not subject to copyright, so the derived per-(dataset, method, metric) values are vendored here with full attribution. Cite Tyler, Guccione and Schadt (2023). beam's role is reanalysis under one consistent ranking rule alongside the other three sources, not redistribution of the paper text or figures.
- `batchbench2021_metrics.csv` and `batchbench2021_datasets.csv`: per-method per-dataset batch entropy and cell-type entropy from BatchBench (Chazarra-Gil et al., Nucleic Acids Research 2021, DOI 10.1093/nar/gkab004). The scores were kindly provided by Ruben Chazarra-Gil, one of the authors, by personal communication (2026-06-04), as the paper's Supplementary Table 1; the dataset descriptors (cells, genes, cell types and batches per dataset) are its Supplementary Table 2. The metric table has eight methods (a `logcounts` uncorrected baseline plus mnnCorrect, limma, ComBat, Seurat3, scanorama, fastMNN, harmony) over 30 datasets from three families (MCA, Tabula Muris, Pancreas); the harmonization keeps the four common methods (combat, harmony, fastMNN, scanorama). The two metrics are off the scIB family but map to the two constructs: batch entropy is higher-is-better (more batch mixing) and cell-type entropy is lower-is-better (a higher value means cell types are more blurred, so less biological structure is kept). Data provided by Chazarra-Gil, personal communication; cite Chazarra-Gil et al. 2021. beam's role is reanalysis under one consistent ranking rule alongside the other sources.
- `integration_published_ranks.csv`: each benchmark's own reported ranking of the five methods, used as the baseline against which beam's consistent re-ranking is compared. Tran from MOESM8 Table S7 `final_rank` (averaged over datasets, then ranked among the five); scIB recomputed as its published 0.6 biological / 0.4 batch weighted overall on its full metric set (min-max scaled within the five common methods per dataset, from `scib-reproducibility` `data/metrics.csv`); OpenProblems from its `mean_score` leaderboard field in the batch_integration `results.json` at the pinned commit `76ce7f2` (the mean of the scaled per-metric scores).

### Dataset crosswalk and overlap

The benchmarks mostly use different datasets, with one confirmed overlap. Tran's Dataset 4 (human pancreas) is built from Muraro (GSE85241), Segerstolpe (E-MTAB-5061), Baron (GSE84133), Wang (GSE83139) and Xin (GSE81608), the same five studies scIB's `pancreas` task uses. Tran and scIB share the pancreas data; a same-data, different-pipeline contrast on it can isolate the benchmarker effect with no data confound. Tran's other datasets (from MOESM1 Table S1): D1 dendritic (Villani), D2 murine atlas (Han, Tabula Muris), D3 simulation, D5 PBMC (Zheng), D6 cell lines (293T, Jurkat), D7 mouse retina (Shekhar, Macosko), D8 mouse brain (Saunders, Rosenberg), D9 bone marrow and cord blood (HCA), D10 mouse haematopoietic (Nestorowa, Paul). OpenProblems uses cellxgene-census atlases (dkd, gtex, hypomap, immune_cell_atlas, mouse_pancreas_atlas, tabula_sapiens), none of which are the Baron/Muraro pancreas, so it does not overlap Tran or scIB.

### Why these five, and what was discarded

The first four (scIB, OpenProblems batch_integration, Tran et al. 2020, Tyler et al. 2023) publish reusable per-method scores on the shared scIB metric family. The first three cover the full five-method block; Tyler covers three of the five methods (harmony, scanorama, liger) and three of the four metric families (ARI, ASW, kBET). BatchBench (Chazarra-Gil et al., NAR 2021) was first set aside here as off-family, since it scores on batch and cell-type entropy rather than the scIB metrics. It is now included as a fifth source after its author shared the scores: the harmonization works on the within-benchmark rank scale, so a benchmark can enter on its own metrics as long as it ranks the common methods, and BatchBench's two metrics map to the batch and biological constructs. Its different metric choice is part of what the cross-benchmark analysis measures rather than a reason to leave it out. Candidates still discarded: scIB-E (Genome Biology 2025, supplement MOESM2 Tables S4 and S12) shares the scIB metrics but its methods are deep-learning ones (scVI, scANVI and loss-function variants), with no overlap with the classical five; the Communications Biology 2025 reference-informed evaluation (DOI 10.1038/s42003-025-07947-7, Zenodo 14898612) covers one dataset with a bespoke RBET metric and overlaps only on combat and scanorama; sc_mixology (Nature Methods 2019) uses off-family metrics; spatial and cross-species benchmarks use different methods; Antonsson and Melsted (PMC12315870, 2025) reports a nearest-neighbour-rank calibration metric that is disjoint from the ARI/ASW/kBET/LISI family and so cannot enter this harmonization on shared metrics (it would be a separate metric-family contrast, future work). This scarcity is consistent with the reviewer survey of scRNA-seq benchmark reproducibility (Genome Biology 2023, DOI 10.1186/s13059-023-02962-5): most benchmarks release code but not per-method results.

## shen2026_metrics.csv

Per-method per-dataset per-scenario integration scores from the semi-supervised scRNA-seq integration benchmark of Shen, He and Guan (PLOS Computational Biology 2026, DOI [10.1371/journal.pcbi.1014008](https://doi.org/10.1371/journal.pcbi.1014008)). Loaded by `beam.datasets.load_semisupervised_integration` and used by the cross-benchmark vignette for the method-agnostic `dataset_discrimination` and `difficulty_concordance` diagnostics, the axis that admits benchmarks whose methods do not overlap the classical five.

Ten methods (five semi-supervised: scANVI, scGEN, STACAS, scDREAMER, ItClust; five unsupervised: Seurat, scVI, Harmony, scanorama, scCRAFT) on six datasets (human pancreas, human immune, lung atlas, lung two-species, macaque, and a mammary `bct` set), each scored under a set of annotation scenarios that degrade label supervision (full supervision, unsupervised, randomly missing or wrong labels at 30/50/70 percent, partially annotated batches, edge mixing, and reference-based Azimuth, CellAssign and singleR transfers). The 13 metrics are the scIB family in scib's scaled form, all in [0, 1] and higher is better: `ARI_cluster/label`, `NMI_cluster/label`, `ASW_label`, `ASW_label/batch`, `isolated_label_F1`, `isolated_label_silhouette`, `graph_conn`, `kBET`, `lisi_b`, `lisi_c`, `lisi_f1`, `pos_rate`, `truepos_rate`. The loader maps the first ten to the bundled cards and treats each (dataset, scenario) pair as one unit. A method or metric not run in a scenario is left as `NA` and read as `numpy.nan`; nothing is imputed.

The table is reduced from the authors' repository (`RainySheena/benchmark_semi`, folder `metrics_by_datasets/results/`, one CSV per dataset) at the pinned commit `f311f17dcc8f2f6fc5eb6a5bc9e16ec2007e4883` by `reduce_shen.py` in this folder, which normalizes the per-file column-layout differences (a BOM on one header, a method/metric column swap, a `file_path`/`embedding_key` naming) into one long table. The repository ships no license file. Numerical results in a published benchmark are facts not subject to copyright, so the derived per-(dataset, scenario, method, metric) scores are vendored here with attribution, the same basis used for the Tyler 2023 and DeepCellSeek 2025 tables; beam's role is reanalysis under one consistent rule, not redistribution of the article text or figures. Cite Shen, He and Guan (2026).

## gptcelltype2024_agreement.csv, gptcelltype2024_features.csv

Cell type annotation agreement scores from the benchmark of Hou and Ji (2024), which scores GPT-4 and GPT-3.5 against three reference-based annotators (CellMarker2.0, SingleR, ScType). Loaded by `beam.datasets.load_gptcelltype`.

### Provenance

Hou W, Ji Z. Assessing GPT-4 for cell type annotation in single-cell RNA-seq analysis. Nature Methods 2024, DOI 10.1038/s41592-024-02235-4. The two tables are derived once from the compiled evaluation table in the paper's reproduction repository at a pinned commit:

```
repo:   github.com/Winnie09/GPTCelltype_Paper
commit: 5944a41511aacd368b45448e256d9625849704df
file:   anno/compiled/all.csv
```

The reduction script is `reduce_gptcelltype.py` in this folder. Run it with no arguments to fetch the file from the pinned commit, or pass a local copy of `all.csv`:

```
python reduce_gptcelltype.py            # fetches the pinned commit
python reduce_gptcelltype.py all.csv    # or reduces a local copy
```

### Shape

`all.csv` has one row per annotated cell type, with a `<method>_agreement` column per method holding the ontology-aware score (1 full match, 0.5 partial match, 0 mismatch). The reduction melts the six method columns to long form.

- `gptcelltype2024_agreement.csv`: 5461 rows, columns `source, tissue, dataset, cell_type, manual_broadtype, method, agreement, broadtype`. One row per cell type per method that was run. The six methods are named GPT-4 (`gpt4aug3`), GPT-4-mar2023 (`gpt4mar23`, a version-robustness subset), GPT-3.5 (`gpt3.5aug3`), CellMarker2.0, SingleR, ScType. `manual_broadtype` is the broad lineage of the manual annotation and `broadtype` is the method's predicted broad lineage (empty when none), kept so a consensus check can compare them.
- `gptcelltype2024_features.csv`: one row per (source, tissue) dataset (54 datasets), columns `dataset, source, tissue, species, sample_type, n_cell_types`. `species` is mouse for the Mouse Cell Atlas (MCA) source and human otherwise; `sample_type` is cancer for the BCL, coloncancer and lungcancer sources and normal otherwise. These are the candidate Bradley-Terry splitting variables.

beam treats each (source, tissue) pair as one dataset and each cell type as one observation within it. The reference-based annotators SingleR and ScType were not run on the Azimuth and literature datasets, and the March 2023 GPT-4 endpoint covers a subset, so `load_gptcelltype` reads those as `numpy.nan` and does not impute them.

### Metric cards

Two cards are minted from this benchmark: `cell_type_annotation_agreement` (the mean per-cell-type agreement) and `cell_type_annotation_full_match_rate` (the fraction of cell types that fully match). Both are higher is better, bounded in [0, 1].

### License

The Hou and Ji (2024) article and its supplementary tables are CC-BY-4.0; the analysis code repository carries Zenodo DOIs (10.5281/zenodo.8317406 for the package, 10.5281/zenodo.8317410 for the analysis). These derived tables are redistributed under CC-BY-4.0 with attribution; cite Hou and Ji (2024).

## deepcellseek2025_agreement.csv, deepcellseek2025_features.csv

A second LLM cell type annotation benchmark, scoring 11 LLM endpoints and the three classical annotators CellMarker2.0, SingleR and ScType on the same ontology-aware agreement metric as Hou and Ji (2024). Loaded by `beam.datasets.load_deepcellseek`, which reuses the `GPTCelltype` container and the two annotation cards.

### Provenance

Xiao T, Hua D, Wang Y, Lu X, Zhang C. Benchmarking large language models for cell typing in single-cell RNA-Seq. Briefings in Bioinformatics 2025, 26(6):bbaf677, DOI 10.1093/bib/bbaf677. The scores are Supplementary Table 4 of the article supplement file `supplementary_table_bbaf677.xlsx` (sheet "Supplementary Table 4"), per cell type per method. The OUP supplement download link is signed and expires, so there is no stable raw URL; download the supplement from the article and run the reduction script `reduce_deepcellseek.py` in this folder:

```
python reduce_deepcellseek.py supplementary_table_bbaf677.xlsx
```

### Shape

`deepcellseek2025_agreement.csv` is long format `source, tissue, dataset, type, cell_type, method, score`, one row per cell type per method, the ontology-aware score (1 full match, 0.5 partial, 0 mismatch). The `type` column is "Broad Cell type", "Subtype" or "Mouse"; `load_deepcellseek` keeps the broad rows by default. `deepcellseek2025_features.csv` has one row per (source, tissue) dataset with `source, tissue, species, n_cell_types`.

### License

The DeepCellSeek article is CC-BY-NC. Numerical results in a published table are facts not subject to copyright, so the derived per-method scores are vendored here with attribution, the same basis used for the Tyler 2023 integration table; beam's role is reanalysis under one consistent rule, not redistribution of the article. Cite Xiao et al. (2025). The off-family SOAR and the LLM-only AnnDictionary benchmarks used in the cross-benchmark section live under `soar/` and `anndictionary/` with their own license notes.
