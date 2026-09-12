# Bundled data

Missing cells are read as `numpy.nan` and are not imputed.

## DuoSCClustering2018.csv

- Source: Duo A, Robinson MD, Soneson C. A systematic performance evaluation of clustering methods for single-cell RNA-seq data. F1000Research 2018, 7:1141. DOI 10.12688/f1000research.15666.3. The table is the one of the bettr app for the DuoClustering2018 Bioconductor package (https://bioconductor.org/packages/DuoClustering2018).
- Shape: 14 methods by 12 datasets by 4 metrics, wide, columns `<metric>_<dataset>`.
- Methods: CIDR, FlowSOM, monocle, PCAHC, PCAKmeans, pcaReduce, RaceID2, RtsneKmeans, SAFE, SC3, SC3svm, Seurat, TSCAN, ascend.
- Datasets: Koh, KohTCC, Kumar, KumarTCC, SimKumar4easy, SimKumar4hard, SimKumar8hard, Trapnell, TrapnellTCC, Zhengmix4eq, Zhengmix4uneq, Zhengmix8eq.
- Metrics: `ARI` is `ari` (higher is better); `elapsed` is `runtime` in seconds; `s.norm.vs.true` is `shannon_entropy_diff`; `nclust.vs.true` is `nclust_deviation` (the last three lower is better).
- Missing: `NA` strings; 5 in `ARI`, 5 in `elapsed`, 5 in `s.norm.vs.true`, 101 in `nclust.vs.true`.
- License: article CC-BY 4.0; package GPL (>= 2).
- Loader: `beam.datasets.load_duo2018`.

## DuoSCClustering2018_features.csv

- One row per Duo 2018 dataset: `dataset, n_cells, n_clusters, source_type, family, quantification`. Splitting variables for `beam.heterogeneity.bradley_terry_tree`.
- `n_cells` and `n_clusters` are the nominal sizes in the DuoClustering2018 help files (https://csoneson.github.io/DuoClustering2018/reference/); the counts after QC can differ slightly.
- `source_type`: the three SimKumar datasets are `simulated`, the rest `real`, as in the paper.
- `family` (Koh, Kumar, SimKumar, Trapnell, Zhengmix) and `quantification` (`standard` or `tcc`) are parsed from the dataset name.
- Loader: `beam.datasets.load_duo2018_features`.

## M4_2018_by_frequency.csv

- Source: Makridakis, Spiliotis and Assimakopoulos (2020), The M4 Competition: 100,000 time series and 61 forecasting methods, International Journal of Forecasting, DOI 10.1016/j.ijforecast.2019.04.014. Computed from the `M4comp2018` R package at commit `3c75dcd25c72c631f04bff1a017d9917d0e7251c` with R 4.3.3. The series are not bundled.
- Shape: the top 25 methods by OWA rank by 6 frequency bands (Yearly, Quarterly, Monthly, Weekly, Daily, Hourly) by 2 metrics. Long, columns `method, frequency, smape, mase, n_series`. Both metrics are lower is better.
- sMAPE is `2*|F-A|/(|F|+|A|)` averaged over the horizon, in percent. MASE scales the mean absolute error by the in-sample seasonal naive error, with period 1 for Yearly, Weekly and Daily, 4 for Quarterly, 12 for Monthly, 24 for Hourly.
- Check: Smyl has an overall sMAPE of 11.374 and MASE of 1.536, as in the M4 paper.
- License: GPL-3, as `M4comp2018`.
- Loader: `beam.datasets.load_m4`.

To reproduce, run:

```
git clone https://github.com/carlanetto/M4comp2018.git
cd M4comp2018 && git lfs pull
Rscript reduce_m4.R
```

## openproblems_batch_integration.csv, openproblems_svg.csv, openproblems_svg_features.csv

- Source: OpenProblems consortium, Nature Biotechnology 2025, DOI 10.1038/s41587-025-02694-w. Files `results/<task>/data/{results,metric_info,dataset_info,method_info}.json` of `github.com/openproblems-bio/website` at commit `76ce7f288da591b1b19c32cbfe8ce50bc3706ece`. The reduction is in `examples/openproblems/openproblems.qmd`.
- `openproblems_batch_integration.csv`: 19 methods by 6 cellxgene-census datasets by 13 scIB metrics (Luecken et al. 2022), without the 7 control and baseline methods. Long, columns `method_id, dataset_id, metric_id, score`. Cards: `ari`, `nmi`, `asw_batch`, `asw_label`, `cell_cycle_conservation`, `graph_connectivity`, `hvg_overlap`, `isolated_label_asw`, `isolated_label_f1`, `kbet`, `ilisi`, `clisi`, `pcr`.
- `openproblems_svg.csv`: 14 methods by 50 spatial datasets by one `correlation` metric, without the 2 baselines.
- `openproblems_svg_features.csv`: `technology`, `organism` and `condition` (cancer or noncancer) of the 50 spatial datasets, parsed from the dataset id.
- All metrics are higher is better.
- License: CC-BY-4.0.
- Loaders: `beam.datasets.load_openproblems`, `beam.datasets.load_openproblems_svg_features`.

## scib2022_metrics.csv, tran2020_metrics.csv, tyler2023_metrics.csv, batchbench2021_metrics.csv, batchbench2021_datasets.csv, integration_published_ranks.csv

Five integration benchmarks for the methods combat, harmony, fastMNN, scanorama and LIGER, on ARI, ASW, kBET and LISI. Loaders: `beam.datasets.load_integration_benchmarks`, `beam.datasets.load_integration_published_ranks`.

- `scib2022_metrics.csv`: Luecken et al., Nature Methods 2022, DOI 10.1038/s41592-021-01336-8. Unscaled rows of `data/metrics.csv` in `theislab/scib-reproducibility` for five real datasets (immune_cell_hum, immune_cell_hum_mou, lung_atlas, mouse_brain, pancreas), columns `ARI_cluster/label`, `ASW_label`, `kBET`, `iLISI`, one variant per method (combat_full, harmony_embed, fastmnn_embed, scanorama_embed, liger_embed). Code MIT, article CC-BY 4.0.
- `tran2020_metrics.csv`: Tran et al., Genome Biology 2020, DOI 10.1186/s13059-019-1850-9, CC-BY 4.0. Additional file 8, Table S7, columns ARI_rank, ASW_rank, LISI_rank, kBET_rank, for nine non-simulation datasets. These are ranks.
- `tyler2023_metrics.csv`: Tyler, Guccione and Schadt, bioRxiv 2021.11.15.468733 v2 (2023-10-26), a preprint under CC-BY-NC-ND 4.0. Extended Data Table 2 sheet A, `observed_metric` averaged over the two `ref_clust_method` variants, for harmony, scanorama and liger on two in silico runs. `ari_celltype` is ARI, `asw` is ASW, `mean_kBET_within_cell_type` is kBET as a rejection rate, lower is better. Its cell-type LISI is not used. Only the numeric values of the table are bundled.
- `batchbench2021_metrics.csv`, `batchbench2021_datasets.csv`: Chazarra-Gil et al., Nucleic Acids Research 2021, DOI 10.1093/nar/gkab004. Supplementary Tables 1 and 2, provided by Ruben Chazarra-Gil by personal communication (2026-06-04). Eight methods over 30 datasets (MCA, Tabula Muris, Pancreas); combat, harmony, fastMNN and scanorama are used. Batch entropy is higher is better and cell-type entropy lower is better. No license is stated.
- `integration_published_ranks.csv`: the ranking each benchmark reported for the five methods. Tran: Table S7 `final_rank`, averaged over datasets and ranked. scIB: the 0.6 biological / 0.4 batch overall score recomputed on its metrics, min-max scaled within the five methods per dataset. OpenProblems: the `mean_score` of the batch_integration `results.json` at commit `76ce7f2`.

Tran's Dataset 4 and the scIB `pancreas` task use the same five studies: Muraro (GSE85241), Segerstolpe (E-MTAB-5061), Baron (GSE84133), Wang (GSE83139) and Xin (GSE81608). `beam.datasets.load_pancreas_contrast` uses them. The other datasets do not overlap between benchmarks.

Not included: scIB-E (Genome Biology 2025), whose methods do not overlap the five; the Communications Biology 2025 evaluation (DOI 10.1038/s42003-025-07947-7), with one dataset and its own metric; sc_mixology (Nature Methods 2019), with other metrics.

## scib2022_dl_metrics.csv

- Source: as `scib2022_metrics.csv`, at commit `5f9c08e213c714db70f96144acd4179f9481c3d2`, reduced by `reduce_scib_dl.py`.
- Shape: six methods (scVI, scANVI, scGen, DESC, SAUCIE, trVAE) by the five real datasets by ARI, ASW, kBET, LISI, unscaled, higher is better. Variants: scvi_embed, scanvi_embed, scgen_full, desc_embed, saucie_embed, trvae_embed. scGen has four datasets and trVAE three.
- License: code MIT, article CC-BY 4.0.
- Loader: `beam.datasets.load_scib_integration_families`.

## shen2026_metrics.csv

- Source: Shen, He and Guan, PLOS Computational Biology 2026, DOI [10.1371/journal.pcbi.1014008](https://doi.org/10.1371/journal.pcbi.1014008). Folder `metrics_by_datasets/results/` of `RainySheena/benchmark_semi` at commit `f311f17dcc8f2f6fc5eb6a5bc9e16ec2007e4883`, reduced by `reduce_shen.py`.
- Shape: ten methods (scANVI, scGEN, STACAS, scDREAMER, ItClust, Seurat, scVI, Harmony, scanorama, scCRAFT) by six datasets by annotation scenarios by 13 scIB metrics in [0, 1], higher is better. The loader maps ten metrics to cards and takes each (dataset, scenario) pair as a unit.
- License: the repository has no license file. Only the numeric scores are bundled.
- Loader: `beam.datasets.load_semisupervised_integration`.

## gptcelltype2024_agreement.csv, gptcelltype2024_features.csv

- Source: Hou W, Ji Z. Assessing GPT-4 for cell type annotation in single-cell RNA-seq analysis. Nature Methods 2024, DOI 10.1038/s41592-024-02235-4. File `anno/compiled/all.csv` of `github.com/Winnie09/GPTCelltype_Paper` at commit `5944a41511aacd368b45448e256d9625849704df`, reduced by `reduce_gptcelltype.py`.
- `gptcelltype2024_agreement.csv`: 5461 rows, columns `source, tissue, dataset, cell_type, manual_broadtype, method, agreement, broadtype`. The score is 1 for a full match, 0.5 for a partial match, 0 for a mismatch. Methods: GPT-4 (`gpt4aug3`), GPT-4-mar2023 (`gpt4mar23`), GPT-3.5 (`gpt3.5aug3`), CellMarker2.0, SingleR, ScType.
- `gptcelltype2024_features.csv`: 54 (source, tissue) datasets, columns `dataset, source, tissue, species, sample_type, n_cell_types`. `species` is mouse for the Mouse Cell Atlas; `sample_type` is cancer for the BCL, coloncancer and lungcancer sources.
- SingleR and ScType were not run on the Azimuth and literature datasets, and GPT-4-mar2023 has a subset.
- Cards: `cell_type_annotation_agreement`, `cell_type_annotation_full_match_rate`.
- License: CC-BY-4.0. Code DOIs 10.5281/zenodo.8317406 and 10.5281/zenodo.8317410.
- Loader: `beam.datasets.load_gptcelltype`.

```
python reduce_gptcelltype.py            # fetches the pinned commit
python reduce_gptcelltype.py all.csv    # or a local copy
```

## deepcellseek2025_agreement.csv, deepcellseek2025_features.csv

- Source: Xiao T, Hua D, Wang Y, Lu X, Zhang C. Benchmarking large language models for cell typing in single-cell RNA-Seq. Briefings in Bioinformatics 2025, 26(6):bbaf677, DOI 10.1093/bib/bbaf677. Supplementary Table 4 of `supplementary_table_bbaf677.xlsx`, downloaded from the article and reduced by `reduce_deepcellseek.py`.
- `deepcellseek2025_agreement.csv`: long, columns `source, tissue, dataset, type, cell_type, method, score`, for 11 LLM endpoints and CellMarker2.0, SingleR and ScType, with the score of Hou and Ji (2024). `type` is "Broad Cell type", "Subtype" or "Mouse"; the loader keeps the broad rows by default.
- `deepcellseek2025_features.csv`: `source, tissue, species, n_cell_types` per dataset.
- License: the article is CC-BY-NC. Only the numeric scores are bundled.
- Loader: `beam.datasets.load_deepcellseek`.

```
python reduce_deepcellseek.py supplementary_table_bbaf677.xlsx
```

The SOAR and AnnDictionary tables are under `soar/` and `anndictionary/`, each with a license note.
