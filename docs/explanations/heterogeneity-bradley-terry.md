# Heterogeneity: Bradley-Terry trees

The [mixed-effects model](heterogeneity-mixed-effects.md) asks how much of the score variation is a method-by-dataset interaction. The Bradley-Terry tree in [`beam.heterogeneity.bradley_terry_tree`](../reference/bradley_terry_tree.qmd) asks another question: which dataset properties produce that interaction, and what is the ranking inside each subgroup. It follows Strobl, Wickelmaier and Zeileis, who combine a Bradley-Terry model with model-based recursive partitioning.

For one metric, each dataset gives a ranking of the methods. The tree works with the pairwise form of that ranking: for every method pair, the dataset records which method scored higher (a win for one, a loss for the other), a tie on an exact equality, or a missing comparison where a method has no score there. The metric polarity orients the comparison, so a lower-is-better metric needs no manual flipping. [`beam.heterogeneity.paired_comparisons`](../reference/paired_comparisons.qmd) builds this design from a method by dataset matrix; it is pure Python and is the part you can inspect without R.

The datasets are the subjects of the model and the methods are the objects being compared. The order is reversed from the usual reading because the tree splits on properties of the datasets.

## The Bradley-Terry model

A Bradley-Terry model turns pairwise wins into a latent strength per method, the worth, with the worths summing to one. The strongest method is the one most likely to win a pairwise comparison. Fit on all datasets at once, it gives a single ranking, the `global_worth` in the report. 

Model-based recursive partitioning fits the Bradley-Terry model at the root, then tests whether the worth parameters are stable across the candidate dataset features. When the stability test flags a feature, the datasets split on it and the model is refit in each child. The recursion continues until no further split is warranted or a node would fall below the minimum size. The result is a tree whose leaves each carry their own Bradley-Terry ranking, with inner nodes that read as "datasets with feature X above threshold Z go this way".

In the context of Strobl and colleagues, instead of one ranking averaged over datasets that may disagree, the tree gives "prefer method A on datasets like this, method B on datasets like that", with a statistical test deciding where the split is real. `reversed_leaves` reports the leaves whose strongest method differs from the global one, the subgroups where the pooled recommendation does not hold.

## The small-sample limit

Recursive partitioning needs enough datasets to support a split. With a dozen datasets the parameter-stability test rarely separates a feature-dependent regime from sampling noise, and the tree reduces to the single flat ranking. The report says so through `did_split` and the summary, rather than inventing a split. This is the same limit the critical-difference diagram and the mixed-effects fit hit on a small benchmark. The tree is useful where there are many datasets carrying real feature variation.

## How to run and R dependency

Call `bradley_terry_tree(matrix, method_names, dataset_names, numeric_features=, categorical_features=, polarity=)`. The features are per-dataset descriptors, numeric ones as continuous splitters and categorical ones as factors; pass at least one. `minsize` sets the smallest leaf and `alpha` the split test level. The report carries the tree nodes (split variables, breakpoints, parameter-stability p-values), the per-leaf worths with standard errors, the leaf assignment per dataset, the global flat ranking, and a plain-language summary. `node_ranking`, `datasets_in_node` and `reversed_leaves` read the leaves.

The fit runs in R's psychotree through a subprocess, so it needs the R toolchain. Check `bttree_available()` first; the conda environment [envs/heterogeneity.yml](https://github.com/imallona/beam/blob/main/envs/heterogeneity.yml) provides psychotree and partykit.

## Related checks

The [mixed-effects model](heterogeneity-mixed-effects.md) measures how much interaction there is; the Bradley-Terry tree locates it in dataset features and reports the subgroup rankings. Leave-one-dataset-out asks whether the composite ranking depends on any one dataset; the [Friedman-Nemenyi diagram](comparing-methods-across-datasets.md) asks whether the methods are statistically separable on a metric. Read together they move from "is there heterogeneity" to "where is it and what do I do about it".

The [Duo 2018 vignette](../../examples/duo2018/duo2018.qmd) works this through on the Adjusted Rand Index (ARI) scores, where the tree degrades to a flat ranking on 12 datasets.

## References

- Strobl, C., Wickelmaier, F., Zeileis, A.. Accounting for individual differences in Bradley-Terry models by means of recursive partitioning. Journal of Educational and Behavioral Statistics (2011). DOI [10.3102/1076998609359791](https://doi.org/10.3102/1076998609359791).
