# 0003 - Bradley-Terry trees plus mixed-effects for heterogeneity, IRT deferred

- Status: Accepted
- Date: 2025-03-01
- Deciders: Izaskun Mallona
- Supersedes: -
- Superseded by: -

## Context

Strobl and Leisch (Biometrical Journal 2024) argue that global rankings on heterogeneous datasets hide the more useful question: which dataset features make method A preferable to method B. beam needs a diagnostic module that answers this.

I first considered Rasch / IRT. Dropped because of the unidimensionality assumption, which benchmarks typically violate.

## Decision

Two methods in the v1 heterogeneity module:

1. Bradley-Terry trees: psychotree::bttree, on partykit.
2. Mixed-effects on benchmark results: lme4, glmmTMB for bounded metrics.

IRT held for Phase 8.

## Consequences

- Tree splits on dataset features give interpretable subgroup rules.
- Mixed-effects splits variance into dataset-driven vs benchmarker-choice-driven.
- R-only module called from Python. Adds latency.
- Bradley-Terry needs pairwise wins, so scores must be pre-processed.
- Mixed models need enough datasets to estimate the variance components.

## Alternatives considered

- IRT (eRm, mirt, py-irt): unidimensionality assumption too strong for v1.
- Single global ranking with no heterogeneity diagnostic: this is what Strobl criticizes.
- Permutation-based subgroup discovery: less interpretable than trees.

## References

- https://onlinelibrary.wiley.com/doi/full/10.1002/bimj.202200104
- https://epub.ub.uni-muenchen.de/11425/
- https://cran.r-project.org/package=psychotree
- https://cran.r-project.org/package=partykit
