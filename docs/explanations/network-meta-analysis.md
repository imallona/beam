# Cross-benchmark network meta-analysis

When several benchmarks aim to evaluate methods for a given task and score an overlapping but not identical set of methods, no single benchmark compares every pair of methods directly. One benchmark covers methods A, B and C, another covers B, C and D, a third drops a method that the others keep. A network meta-analysis pools the direct and the indirect evidence into one coherent ranking. 

Clinical research uses it to rank treatments that were never all tried head to head in one trial. [`beam.heterogeneity.network_meta_analysis`](../reference/network_meta_analysis.qmd) does this for benchmark results, following the frequentist network meta-analysis of Rucker and Schwarzer as implemented in R's netmeta.

## Rationale

The treatments are the methods. The studies are the (benchmark, dataset) blocks. Within a study, each method has a mean rank over the metrics, and a standard deviation across those metrics. `meta::pairwise` turns the arm-level means into study-level contrasts, and `netmeta` pools them. The output is a treatment effect for each method relative to a reference, a P-score for each method, and the heterogeneity and inconsistency statistics.

The P-score is the ranking. It is the share of competing methods a method outperforms, averaged over the ranking uncertainty, in 0 to 1. Because a benchmark rank of 1 is best, beam treats small values as desirable, so a higher P-score indicates a higher-ranked method.

Benchmarks publish one score per method per dataset per metric, with no replicate runs, so there is no sampling standard error in the usual sense. This wrapper takes the variability across the metrics within a (benchmark, dataset) block as the within-arm spread. That treats the metrics as repeated readings of the same quantity, which they are not exactly: the Adjusted Rand Index (ARI), average silhouette width (ASW), k-nearest-neighbour batch-effect test (kBET) and local inverse Simpson index (LISI) measure related but distinct aspects of integration quality. The pooled ranking is a descriptive summary of the evidence as published, not an inference back to a population of runs. An arm resting on fewer than two metrics has no estimable standard deviation and is dropped, and netmeta then keeps only the studies that still have two or more arms.

Two scores evaluate the pooled ranking. The heterogeneity Q (the within-design part) measures how much the studies of the same design disagree beyond chance. The inconsistency Q (the between-design part) measures whether the direct and the indirect evidence for the same comparison agree. A large inconsistency Q is the formal version of "the benchmarks contradict each other". The ranking that pools them is then an average over evidence that does not line up. beam reports both parts where the design structure supports the split, along with tau-squared and I-squared.

## Related checks

The network meta-analysis and the source-variance decomposition (see [the mixed-effects explanation](method-by-dataset-heterogeneity.md)) answer complementary questions. The mixed-effects [`source_variance_decomposition`](../reference/source_variance_decomposition.qmd) puts a number on how much of the spread is the benchmark rather than the method (the method-by-benchmark variance share). The network meta-analysis pools the same evidence into a single ranking with a hierarchy of methods, and its inconsistency statistic is the disagreement read as a model lack-of-fit rather than as a variance component. A high method-by-benchmark variance share and a significant inconsistency Q both say the benchmarks disagree, so the pooled ranking averages over that disagreement. [Attribution synthesis](attribution-synthesis.md) combines this with the analyst-choice and dataset axes.

## How to run and R dependency

Call `network_meta_analysis(treatment, study, mean, sd, n)` with five parallel sequences, one entry per study arm. `IntegrationBenchmarks.network_arms()` builds them from the harmonized cross-benchmark set (study = benchmark and dataset, treatment = method, mean and sd and count over the metrics). The report carries the per-treatment effect against the reference with its confidence interval, the P-scores, the ranking, and the heterogeneity and inconsistency statistics.

The fit runs in R's netmeta through a subprocess, so it needs the R toolchain. Check `netmeta_available()` first; the conda environment [envs/heterogeneity.yml](https://github.com/imallona/beam/blob/main/envs/heterogeneity.yml) provides it. The [cross-benchmark vignette](../../examples/cross_benchmark/cross_benchmark.qmd) works this through on the four single-cell integration benchmarks.

## References

- Rucker, G.. Network meta-analysis, electrical networks and graph theory. Research Synthesis Methods (2012). DOI [10.1002/jrsm.1058](https://doi.org/10.1002/jrsm.1058).
- Rucker, G., Schwarzer, G.. Ranking treatments in frequentist network meta-analysis works without resampling methods. BMC Medical Research Methodology (2015). DOI [10.1186/s12874-015-0060-8](https://doi.org/10.1186/s12874-015-0060-8).
