# Reference audit, 2026-05-28

Scope. Every DOI and arXiv id across PLAN.md, README.md, CHANGELOG.md, AUTHORS, CITATION.cff, ADRs 0001 to 0015, findings 0001 to 0006, the explanations, tutorials and how-to docs, and the 27 metric cards under src/beam/metrics/<id>/v1.yaml. Each DOI was looked up against Crossref and the title and first author were compared with the citation in the document. arXiv ids were looked up against arxiv.org and compared the same way. The ontology IRIs (STATO, UO, OBI) on the cards are not DOIs and were not part of this pass.

## Verified

| File | Line | Identifier | Title returned by Crossref or arXiv | Status |
|---|---|---|---|---|
| PLAN.md | 561 | 10.1186/s13059-019-1850-9 | A benchmark of batch-effect correction methods for single-cell RNA sequencing data, Tran, Genome Biology 2020 | ok |
| PLAN.md | 562 | 10.1038/s41592-021-01336-8 | Benchmarking atlas-level data integration in single-cell genomics, Luecken, Nature Methods 2022 | ok |
| PLAN.md | 563 | 10.1093/nar/gkab004 | Flexible comparison of batch correction methods for single-cell RNA-seq using BatchBench, Chazarra-Gil, Nucleic Acids Research 2021 | ok |
| PLAN.md | 564 | 10.1186/s13059-025-03869-z | Benchmarking deep learning methods for biologically conserved single-cell integration, Yi, Genome Biology 2025 | ok |
| PLAN.md | 565, 593 | 10.1038/s41587-025-02694-w | Defining and benchmarking open problems in single-cell analysis, Luecken, Nature Biotechnology 2025 | ok |
| PLAN.md | 566 | 10.1038/s41592-025-02856-3 | Multitask benchmarking of single-cell multimodal omics integration methods, Liu, Nature Methods 2025 | ok |
| PLAN.md | 566 | 10.1038/s41467-023-37126-3 | Benchmarking integration of single-cell differential expression, Nguyen, Nature Communications 2023 | ok |
| PLAN.md | 575 | 10.1038/s42003-025-07947-7 | Reference-informed evaluation of batch correction for single-cell omics data with overcorrection awareness, Hu, Communications Biology 2025 | ok |
| PLAN.md | 580 | 10.1186/s13059-023-02962-5 | Meta-analysis of (single-cell method) benchmarks reveals the need for extensibility and interoperability, Sonrel, Genome Biology 2023 | ok |
| PLAN.md | 750 | 10.1186/s13326-016-0100-2 | The Ontology of Biological and Clinical Statistics (OBCS), Zheng, Journal of Biomedical Semantics 2016 | ok |
| PLAN.md | 765 | 10.1002/bimj.202200104 | Against the "one method fits all data sets" philosophy for comparison studies in methodological research, Strobl, Biometrical Journal | ok |
| PLAN.md | 774 | 10.1007/s10994-025-06873-3 | Novel applications of item response theory for analysing data set complexity and benchmark selection, Pereira, Machine Learning 2025 | ok |
| PLAN.md | 776 | arXiv:2203.01282 | py-irt: A Scalable Item Response Theory Library for Python, Lalor, 2022 | ok |
| PLAN.md | 173, 738, 773 | arXiv:2505.15055 | Lost in Benchmarks? Rethinking LLM Benchmarking with IRT, Zhou, 2025 | ok |
| PLAN.md | 781 | 10.1186/s13059-024-03266-y | Commonly used software tools produce conflicting and overly-optimistic AUPRC values, Chen, Genome Biology 2024 | ok |
| README.md | 51 | 10.1186/s13059-024-03266-y | Commonly used software tools produce conflicting and overly-optimistic AUPRC values, Chen, Genome Biology 2024 | ok |
| docs/adr/0001-yaml-cards-not-owl.md | 35 | arXiv:2204.01075 | Data Cards: Purposeful and Transparent Dataset Documentation for Responsible AI, Pushkarna, 2022 | ok |
| docs/adr/0001-yaml-cards-not-owl.md | 36 | arXiv:1810.03993 | Model Cards for Model Reporting, Mitchell, 2018 | ok |
| docs/adr/0003-bradley-terry-not-irt.md | 40 | 10.1002/bimj.202200104 | Against the "one method fits all data sets" philosophy, Strobl, Biometrical Journal | ok |
| docs/adr/0011-glmmtmb-and-plackett-luce.md | 43 | 10.32614/RJ-2017-066 | glmmTMB Balances Speed and Flexibility Among Packages for Zero-inflated Generalized Linear Mixed Modeling, Brooks, The R Journal 2017 | ok |
| docs/adr/0011-glmmtmb-and-plackett-luce.md | 44 | 10.1007/s00180-020-00959-3 | Modelling rankings in R: the PlackettLuce package, Turner, Computational Statistics 2020 | ok |
| docs/adr/0011-glmmtmb-and-plackett-luce.md | 45 | 10.1037/1082-989X.11.1.54 | A better lemon squeezer? Maximum-likelihood regression with beta-distributed dependent variables, Smithson, Psychological Methods 2006 | ok |
| docs/adr/0014-skillings-mack-for-coverage-aware-friedman.md | 37 | 10.1080/00401706.1981.10486261 | On the Use of a Friedman-Type Statistic in Balanced and Unbalanced Block Designs, Skillings, Technometrics 1981 | ok |
| docs/explanations/skillings-mack.md | 57 | 10.1080/00401706.1981.10486261 | Same as above | ok |
| docs/explanations/openproblems-as-a-data-source.md | 3 | 10.1038/s41587-025-02694-w | Defining and benchmarking open problems in single-cell analysis, Luecken, Nature Biotechnology 2025 | ok |
| docs/findings/0001-duo-2018-mcda.md | 33 | 10.12688/f1000research.15666.3 | A systematic performance evaluation of clustering methods for single-cell RNA-seq data, Duo, F1000Research | ok |
| docs/findings/0002-duo-2018-variance-decomposition.md | 33 | 10.12688/f1000research.15666.3 | Same as above | ok |
| docs/findings/0003-duo-2018-bradley-terry-tree.md | 33 | 10.12688/f1000research.15666.3 | Same as above | ok |
| docs/findings/0004-openproblems-svg-bradley-terry.md | 40 | 10.1038/s41587-025-02694-w | Luecken, Nature Biotechnology 2025 | ok |
| docs/findings/0005-cross-benchmark-integration-agreement.md | 43 | 10.1038/s41592-021-01336-8 | Luecken, Nature Methods 2022 | ok |
| docs/findings/0005-cross-benchmark-integration-agreement.md | 43 | 10.1186/s13059-019-1850-9 | Tran, Genome Biology 2020 | ok |
| docs/findings/0005-cross-benchmark-integration-agreement.md | 43 | 10.1038/s41587-025-02694-w | Luecken, Nature Biotechnology 2025 | ok |
| docs/findings/0005-cross-benchmark-integration-agreement.md | 43 | 10.1101/2021.11.15.468733 | Erasure of Biologically Meaningful Signal by Unsupervised scRNAseq Batch-correction Methods, Tyler, bioRxiv 2021 (revised 2023) | ok |
| docs/findings/0006-pancreas-same-data-contrast.md | 47 | 10.1038/s41592-021-01336-8 | Luecken, Nature Methods 2022 | ok |
| docs/findings/0006-pancreas-same-data-contrast.md | 47 | 10.1186/s13059-019-1850-9 | Tran, Genome Biology 2020 | ok |
| src/beam/metrics/ari/v1.yaml | 14 | 10.1007/BF01908075 | Comparing partitions, Hubert and Arabie, Journal of Classification 1985 | ok |
| src/beam/metrics/silhouette/v1.yaml | 14 | 10.1016/0377-0427(87)90125-7 | Silhouettes: a graphical aid to the interpretation and validation of cluster analysis, Rousseeuw, J Comput Appl Math 1987 | ok |
| src/beam/metrics/asw_label/v1.yaml | 11 | 10.1016/0377-0427(87)90125-7 | Same Rousseeuw 1987 | ok |
| src/beam/metrics/asw_label/v1.yaml | 14 | 10.1038/s41592-021-01336-8 | Luecken 2022 | ok |
| src/beam/metrics/asw_batch/v1.yaml | 11 | 10.1016/0377-0427(87)90125-7 | Rousseeuw 1987 | ok |
| src/beam/metrics/asw_batch/v1.yaml | 14 | 10.1038/s41592-021-01336-8 | Luecken 2022 | ok |
| src/beam/metrics/calibration_slope/v1.yaml | 11 | 10.1186/s12916-019-1466-7 | Calibration: the Achilles heel of predictive analytics, Van Calster, BMC Medicine 2019 | ok |
| src/beam/metrics/cell_cycle_conservation/v1.yaml | 11 | 10.1126/science.aad0501 | Dissecting the multicellular ecosystem of metastatic melanoma by single-cell RNA-seq, Tirosh, Science 2016 | ok |
| src/beam/metrics/cell_cycle_conservation/v1.yaml | 14 | 10.1038/s41592-021-01336-8 | Luecken 2022 | ok |
| src/beam/metrics/clisi/v1.yaml | 11 | 10.1038/s41592-019-0619-0 | Fast, sensitive and accurate integration of single-cell data with Harmony, Korsunsky, Nature Methods 2019 | ok |
| src/beam/metrics/clisi/v1.yaml | 14 | 10.1038/s41592-021-01336-8 | Luecken 2022 | ok |
| src/beam/metrics/ilisi/v1.yaml | 11 | 10.1038/s41592-019-0619-0 | Korsunsky 2019 | ok |
| src/beam/metrics/ilisi/v1.yaml | 14 | 10.1038/s41592-021-01336-8 | Luecken 2022 | ok |
| src/beam/metrics/graph_connectivity/v1.yaml | 11 | 10.1038/s41592-021-01336-8 | Luecken 2022 | ok |
| src/beam/metrics/hvg_overlap/v1.yaml | 11 | 10.1038/s41592-021-01336-8 | Luecken 2022 | ok |
| src/beam/metrics/isolated_label_asw/v1.yaml | 11 | 10.1038/s41592-021-01336-8 | Luecken 2022 | ok |
| src/beam/metrics/isolated_label_f1/v1.yaml | 11 | 10.1038/s41592-021-01336-8 | Luecken 2022 | ok |
| src/beam/metrics/kbet/v1.yaml | 11 | 10.1038/s41592-018-0254-1 | A test metric for assessing single-cell RNA-seq batch correction, Buttner, Nature Methods 2019 | ok |
| src/beam/metrics/kbet/v1.yaml | 14 | 10.1038/s41592-021-01336-8 | Luecken 2022 | ok |
| src/beam/metrics/pcr/v1.yaml | 11 | 10.1038/s41592-018-0254-1 | Buttner 2019 | ok |
| src/beam/metrics/pcr/v1.yaml | 14 | 10.1038/s41592-021-01336-8 | Luecken 2022 | ok |
| src/beam/metrics/mase/v1.yaml | 15 | 10.1016/j.ijforecast.2006.03.001 | Another look at measures of forecast accuracy, Hyndman and Koehler, IJF 2006 | ok |
| src/beam/metrics/mase/v1.yaml | 17 | 10.1016/j.ijforecast.2019.04.014 | The M4 Competition: 100,000 time series and 61 forecasting methods, Makridakis, IJF 2020 | ok |
| src/beam/metrics/smape/v1.yaml | 16 | 10.1016/0169-2070(93)90079-3 | Accuracy measures: theoretical and practical concerns, Makridakis, IJF 1993 | ok |
| src/beam/metrics/smape/v1.yaml | 18 | 10.1016/j.ijforecast.2019.04.014 | Makridakis 2020 | ok |
| src/beam/metrics/nclust_deviation/v1.yaml | 11 | 10.12688/f1000research.15666.3 | Duo 2018 | ok |
| src/beam/metrics/shannon_entropy_diff/v1.yaml | 11 | 10.12688/f1000research.15666.3 | Duo 2018 | ok |

## Fixed in place

No DOI typos were fixed. The audit found no off-by-one or missing-slash typos.

## Needs human review

One reference has a substantive mismatch.

| File | Line | Problem | Proposed fix |
|---|---|---|---|
| src/beam/metrics/correlation/v1.yaml | 8 to 10 | The card cites "Spearman C. The proof and measurement of association between two things" with DOI 10.1093/biomet/30.1-2.81. That DOI resolves to Kendall M. G., "A new measure of rank correlation", Biometrika 30(1-2):81-93, 1938, which is Kendall's tau, not Spearman's rank correlation. The card text is for Spearman; the DOI is for Kendall. | Either swap the DOI to 10.2307/1412159 (Spearman, "The Proof and Measurement of Association between Two Things", American Journal of Psychology 1904) and keep the Spearman wording, or keep the DOI 10.1093/biomet/30.1-2.81 and rewrite the citation text to Kendall. Note OpenProblems' spatially-variable-genes task uses Spearman rank correlation, so the Spearman citation is the consistent choice. |

## Counts

Verified: 60 reference checks across 33 unique identifiers (29 DOIs and 4 arXiv ids). Fixed in place: 0. Needs human review: 1.

Most surprising finding: every DOI in PLAN.md and in the ADR and findings docs resolved cleanly. The single mismatch is in a metric card whose citation text and DOI point to two different rank-correlation papers from the same Biometrika journal family, where Spearman's text was paired with Kendall's tau DOI.
