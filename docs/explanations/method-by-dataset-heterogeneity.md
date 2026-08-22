# Method-by-dataset heterogeneity

A pooled [MCDA](aggregation-methods.md) ranking reports one order of the methods for all datasets. `beam.heterogeneity` has four models of whether that order is stable across datasets. Each takes the method by dataset scores of one metric and fits in R:

- mixed-effects variance decomposition: the share of the score variance that is method-by-dataset interaction;
- Bradley-Terry tree: the dataset features behind the interaction, and the ranking in each subgroup;
- Plackett-Luce: one ranking with uncertainty from full orderings per dataset;
- glmmTMB beta: the mixed-effects decomposition for a metric bounded in (0, 1).

## Mixed-effects variance decomposition

[`beam.heterogeneity.mixed_effects`](../reference/mixed_effects.qmd) follows Eugster, Hothorn and Leisch (2008). Every score of one metric is an observation with a method and a dataset:

    score ~ method + (1 | dataset)

The method is a fixed effect, with a marginal mean and standard error per method. The dataset is a random intercept for the difficulty of each dataset.

The intraclass correlation is the dataset variance over the total. A high value means the datasets differ in difficulty; a low value means most variation is within datasets, where the method-by-dataset interaction is.

With one run per method and dataset, the interaction is not separable from noise, and the residual share is its upper bound. With replicates the model is

    score ~ method + (1 | dataset) + (1 | dataset:method)

and `interaction_share` is defined instead of `None`.

`top_outliers` returns the cells with the largest residuals: methods that do much better or worse on a dataset than their marginal mean predicts.

`mixed_effects(methods, datasets, scores)` takes three parallel sequences, and `mixed_effects_from_matrix(matrix, method_names, dataset_names)` a method by dataset matrix. NaN scores are dropped. The report has the marginal means and standard errors, the variance components, the dataset ICC, the interaction or residual share, the residuals, and the outlier cells.

## Bradley-Terry trees

[`beam.heterogeneity.bradley_terry_tree`](../reference/bradley_terry_tree.qmd) combines a Bradley-Terry model with model-based recursive partitioning (Strobl, Wickelmaier and Zeileis 2011).

For every pair of methods, each dataset records which scored higher, a tie, or a missing comparison. The metric polarity orients the comparison. [`beam.heterogeneity.paired_comparisons`](../reference/paired_comparisons.qmd) builds this design in Python. The datasets are the subjects and the methods the objects compared.

A Bradley-Terry model gives a worth per method, summing to one; fitted on all datasets it is the `global_worth`. Recursive partitioning tests whether the worths are stable across the dataset features, splits the datasets on a feature that fails the test, and refits in each child, until no split is significant or a node is below the minimum size. Each leaf has its own ranking. `reversed_leaves` lists the leaves whose top method differs from the global one.

With about a dozen datasets the stability test rarely finds a split; `did_split` reports it.

`bradley_terry_tree(matrix, method_names, dataset_names, numeric_features=, categorical_features=, polarity=)` needs at least one feature. `minsize` is the smallest leaf and `alpha` the level of the split test. The report has the tree nodes (split variables, breakpoints, p-values), the worths with standard errors per leaf, the leaf of each dataset, the global ranking, and a summary. `node_ranking`, `datasets_in_node` and `reversed_leaves` read the leaves.

## Plackett-Luce: full rankings

Plackett-Luce estimates one worth per method from the full ranking of the methods on each dataset. It reduces to Bradley-Terry for pairwise data.

[`beam.heterogeneity.plackett_luce`](../reference/plackett_luce.qmd) builds the ranking per dataset from the score matrix, oriented by the polarity. Ties are shared, and a method missing on a dataset is left out of that ranking. The report has the worth, the log-worth, the quasi-standard-errors, which compare any two methods without a baseline, and whether the ranking network is connected. With ties and partial coverage the quasi-standard-errors can fail; the worths are reported and the standard errors are NA with a warning.

## glmmTMB beta: bounded metrics

The lme4 model assumes a Gaussian residual, an approximation for a metric bounded in (0, 1). `mixed_effects(engine="glmmtmb", family="beta")` fits the same model with a beta likelihood. The marginal means and variance components are on the logit scale (`scale` is "link") and are not comparable to the lme4 values; the method ordering is. The auto family is beta only for scores strictly in (0, 1).

## R dependency

The models run in an R subprocess: lme4 for the Gaussian mixed-effects fit, psychotree and partykit for the tree, PlackettLuce and qvcalc for Plackett-Luce, glmmTMB for the beta engine. `r_available()`, `bttree_available()`, `plackett_luce_available()` and `glmmtmb_available()` check them. The conda environment [envs/heterogeneity.yml](https://github.com/imallona/beam/blob/main/envs/heterogeneity.yml) has all of them.

## See also

- [`beam.mcda.leave_one_dataset_out`](../reference/leave_one_dataset_out.qmd)
- [Critical difference](critical-difference.md)
- [Duo 2018 vignette](../../examples/duo2018/duo2018.qmd)

## References

- Eugster, M. J. A., Hothorn, T., Leisch, F. (Psycho-)analysis of benchmark experiments. Technical Report 30, Department of Statistics, LMU Munich (2008).
- Strobl, C., Wickelmaier, F., Zeileis, A. Accounting for individual differences in Bradley-Terry models by means of recursive partitioning. Journal of Educational and Behavioral Statistics (2011). DOI [10.3102/1076998609359791](https://doi.org/10.3102/1076998609359791).
