# Cross-benchmark network meta-analysis

When several benchmarks score overlapping sets of methods, no benchmark compares every pair directly. A network meta-analysis pools the direct and indirect evidence into one ranking. [`beam.heterogeneity.network_meta_analysis`](../reference/network_meta_analysis.qmd) follows the frequentist network meta-analysis of Rucker and Schwarzer in R's netmeta.

## Method

The treatments are the methods and the studies are the (benchmark, dataset) pairs. In a study each method has a mean rank over the metrics and a standard deviation across them. `meta::pairwise` computes the study-level contrasts and `netmeta` pools them into an effect per method relative to a reference, a P-score per method, and heterogeneity and inconsistency statistics.

The P-score is the share of the other methods a method outperforms, averaged over the ranking uncertainty, in 0 to 1. A higher P-score is a better rank.

Benchmarks publish one score per method, dataset and metric, without replicates. The standard deviation across the metrics of a study is used as the within-arm spread. This treats the metrics as repeated measures of one quantity, which they are not, so the pooled ranking is descriptive. An arm with fewer than two metrics is dropped, and netmeta keeps the studies with two or more arms.

The heterogeneity Q (within designs) measures how much studies of the same design disagree. The inconsistency Q (between designs) measures whether direct and indirect evidence for the same comparison agree. beam reports both where the design allows, with tau-squared and I-squared.

## Usage

`network_meta_analysis(treatment, study, mean, sd, n)` takes five parallel sequences, one entry per study arm. `IntegrationBenchmarks.network_arms()` builds them from the bundled integration benchmarks. The report has the effect of each treatment against the reference with its confidence interval, the P-scores, the ranking, and the heterogeneity and inconsistency statistics.

The fit needs R with netmeta; `netmeta_available()` checks it, and the conda environment [envs/heterogeneity.yml](https://github.com/imallona/beam/blob/main/envs/heterogeneity.yml) has it.

## See also

- [`source_variance_decomposition`](../reference/source_variance_decomposition.qmd) and the [mixed-effects models](method-by-dataset-heterogeneity.md)
- [Attribution synthesis](attribution-synthesis.md)
- [Cross-benchmark vignette](../../examples/cross_benchmark/cross_benchmark.qmd)

## References

- Rucker, G.. Network meta-analysis, electrical networks and graph theory. Research Synthesis Methods (2012). DOI [10.1002/jrsm.1058](https://doi.org/10.1002/jrsm.1058).
- Rucker, G., Schwarzer, G.. Ranking treatments in frequentist network meta-analysis works without resampling methods. BMC Medical Research Methodology (2015). DOI [10.1186/s12874-015-0060-8](https://doi.org/10.1186/s12874-015-0060-8).
