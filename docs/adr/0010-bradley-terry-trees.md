# 0010 - Bradley-Terry trees via a one-shot R subprocess

- Status: Accepted
- Date: 2026-05-26
- Deciders: Izaskun Mallona
- Supersedes: -
- Superseded by: -

## Context

PLAN Section 4.1 commits to Bradley-Terry trees (Strobl, Wickelmaier, Zeileis) as the headline interpretable heterogeneity tool: split the datasets by their features so each leaf has its own method ranking, and let a parameter-stability test decide where the global ranking really falls apart. [ADR 0003](0003-bradley-terry-not-irt.md) already chose Bradley-Terry trees over item response theory. [ADR 0009](0009-heterogeneity-mixed-effects-via-r.md) chose a one-shot R subprocess over reticulate for the mixed-effects wrapper. What was open here: how to turn a method by dataset score matrix into the model input, and whether to fit a tree or a single flat Bradley-Terry model.

## Decision

Build the tree input as paired comparisons per dataset and fit a tree, not a flat model.

- Input design. For each dataset and each method pair, the higher score on the chosen metric is a win, the lower a loss, an exact tie a tie, and a missing cell a missing comparison. The metric polarity orients the comparison so a lower-is-better metric is handled without flipping the data. This is the `psychotools::paircomp` shape; the construction is `beam.heterogeneity.paired_comparisons`, a pure-Python function tested without R. The datasets are the subjects whose features split the tree; the methods are the objects compared.
- Model. Fit `psychotree::bttree(preference ~ features)`, which combines a Bradley-Terry model with model-based recursive partitioning (partykit MOB). A flat Bradley-Terry model gives one ranking and cannot answer the heterogeneity question; the tree finds the dataset features that reverse the ranking and reports a per-leaf ranking, which is the point of Section 4.1.
- Boundary. Same one-shot subprocess as ADR 0009. `beam.heterogeneity.bradley_terry_tree` serialises the comparisons and the dataset features to JSON, runs `src/beam/heterogeneity/bradley_terry.R`, and parses the JSON it prints. The shared subprocess machinery (locate Rscript, probe for packages, run with a timeout, parse the output) was factored out of the mixed-effects wrapper into `beam.heterogeneity._rsubprocess` so both wrappers share one path. psychotree and partykit join `envs/heterogeneity.yml`.

## Consequences

- The R dependency stays optional and runtime-discovered, through `bttree_available()` (psychotree and jsonlite). beam installs and imports without R; only this call needs it. The Python test job skips the fits; the conda CI job runs them.
- The report carries the tree structure (split variables, breakpoints, parameter-stability p-values), the per-leaf Bradley-Terry strengths with standard errors, the leaf assignment per dataset, and a global flat fit as the reference ranking. `reversed_leaves` names the subgroups where the pooled top method does not hold, the output the tool exists to produce.
- Small-sample limit. Recursive partitioning needs enough datasets to support a split. With a dozen datasets (the Duo 2018 case) the test usually finds no stable split, and the report degrades to the single flat Bradley-Terry ranking and says so. This is the same small-N limit the critical-difference diagram shows on Duo. The tree earns its keep on a benchmark with many datasets carrying real feature variation (the OpenProblems tasks in PLAN Phase 5 are the intended richer input).
- The partykit split accessors differ across versions, so the R script reads the split variable, breakpoint, and p-values defensively: each risky read degrades to a null value rather than aborting the fit. The worths and the leaf assignment, which use the stable public API, are always returned.

## Alternatives considered

- A flat Bradley-Terry model only. Simpler, but it answers the ranking question, not the heterogeneity question. It is kept as the `global_worth` reference inside the tree report rather than as the headline.
- A native Python Bradley-Terry tree. There is no maintained Python port of model-based recursive partitioning with the parameter-stability machinery; reimplementing it would duplicate psychotree at a high correctness cost. The subprocess reuses the validated R implementation.
- Plackett-Luce on full per-dataset rankings (R PlackettLuce). The natural input here is a score matrix, which gives pairwise wins directly; Plackett-Luce is the documented Phase 4 extension for when the input is a per-dataset ranking, and it reduces to Bradley-Terry on pairwise data.

## References

- [Bradley-Terry trees explanation](../explanations/heterogeneity-bradley-terry.md)
- [ADR 0003 (bradley-terry-not-irt)](0003-bradley-terry-not-irt.md), [ADR 0009 (mixed-effects via R)](0009-heterogeneity-mixed-effects-via-r.md)
- Strobl C, Wickelmaier F, Zeileis A. Accounting for individual differences in Bradley-Terry models by means of recursive partitioning. Journal of Educational and Behavioral Statistics 2011. psychotree: https://cran.r-project.org/package=psychotree
- Zeileis A, Hothorn T, Hornik K. Model-based recursive partitioning. partykit: https://cran.r-project.org/package=partykit
