# 0013 - Missing-data policy for the MCDA pipeline

- Status: Accepted
- Date: 2026-05-27
- Deciders: Izaskun Mallona
- Supersedes: -
- Superseded by: -

## Context

Benchmark score matrices have holes. A method fails to run on a dataset, errors on an input shape, times out, or is simply never evaluated on one metric. In bioinformatics these gaps are common, not rare. beam reads such matrices and must decide what a missing cell means before it can rank.

The pipeline had no policy. Each lower-level function did something different and silent when handed a NaN: min-max and the objective weight schemes propagated NaN through their column statistics; SAW and PROMETHEE II passed NaN straight into pymcdm; TOPSIS, VIKOR and COMET let pymcdm return NaN and then masked it to 0.5; the Friedman ranks were taken over columns that included NaN. The 0.5 mask is the worst of these: it invents a mid-range score for a method that never ran, which is imputation done silently and without the user's say.

Two facts shape the decision. First, a missing score is information about coverage, not a hole to patch; filling it changes the comparison. Second, a missing cell often means "the method did not even run", which a user may reasonably want to score as a failure, but that is a judgment about the benchmark, not something the software should assume.

## Decision

beam never picks a missing-data policy for the user. The tool by metric ranking entry points (`run`, `run_from_registry`, `beam.rank`, the CLI `beam rank --on-missing`, and the `missing` key in beam.yaml) take an explicit policy, default `"error"`.

- `error` (default): any missing cell raises `IncompleteMatrixError`, naming the offending cells and the alternatives. beam refuses rather than guesses.
- `available`: available-case. SAW scores each tool on the metrics it was measured on, with the weights renormalized over that tool's observed support. On a complete row this is the ordinary weighted sum, so the result is unchanged when nothing is missing. Only SAW supports this; see below. A warning records that the composites then rest on different metric supports across tools.
- `worst`: the explicit "did not run = worst" policy. After normalization each missing cell is set to 0, the worst score on the higher-is-better [0, 1] scale. The matrix is then complete, and every method and weighting runs. This is a declared decision about the benchmark, not imputation of an unknown value, and a warning records it.
- `impute`: mean imputation. Each missing cell is filled with the per-metric mean of the observed normalized scores. Discouraged and never a default; it exists only because a user may explicitly want it, and it warns that it fabricates values and biases toward the column mean.

Only SAW has a partial-coverage form that does not complete the matrix, because its composite is a per-tool sum that can be taken over a subset of metrics. TOPSIS and VIKOR need an ideal and anti-ideal point and a full-length distance per tool; PROMETHEE II compares every pair across all criteria; COMET needs a membership per criterion; the objective weight schemes (entropy, standard deviation, CRITIC, MEREC) measure spread across tools and need a complete column. None of these can run on a partial matrix without first completing it, so under `available` they refuse and point the user to `worst`, `impute`, or a per-subset analysis. The Friedman-Nemenyi critical-difference test likewise needs complete blocks and refuses missing cells; its missing-data generalization is the Skillings-Mack (1981) test, left as future work.

Normalization is NaN-transparent: each column's anchors come from the observed values and a missing cell passes through as NaN. This keeps the primitive correct on partial input without imputing, and it is what lets the policy act on the normalized matrix.

The dataset axis is separate and unchanged. `beam.mcda.reduce_tensor` summarizes a tool over the datasets where it actually ran (available-case), which is not imputation; it estimates a tool's performance from the runs that exist. A tool with no run at all for a metric has zero coverage; by default that raises, and `on_zero_coverage="nan"` instead leaves the cell missing so the tool by metric `missing` policy resolves it. `beam.rank` wires these together: it summarizes the tensor first, then applies the `missing` policy to whatever gaps remain.

## Consequences

- The common failure mode, a method missing on some datasets, is handled by the dataset-axis available-case summary as before. The new policy governs the tool by metric layer: a method that never ran a metric, or a wide table with blank cells.
- The default refuses, so a partial input no longer ranks silently. A user who hits the error is told the three explicit choices. This is stricter than before but matches the project's stance that a recommendation must not rest on a hidden methodological choice.
- The 0.5 masking of NaN in TOPSIS, VIKOR and COMET is gone; those methods now refuse a missing input outright. The 0.5 tie convention stays only for genuinely complete but degenerate inputs (a single tool, or rows identical on every metric).
- Every non-error policy records a loud warning on the `Result`, which the HTML report and the CLI surface, so the missing-data treatment is always visible.
- The sensitivity primitives (SMAA, leave-one-metric-out, smallest-weight-perturbation, leave-one-dataset-out) take the same policy. Under `available`, leave-one-metric-out skips an omission that would leave a tool with no observed metric, and the perturbation search skips a criterion one of the pair lacks.

## Alternatives considered

- Impute by default (mean, zero, or a degenerate 0.5). Rejected: it fabricates scores the method never earned and hides the choice. Mean imputation survives only as an explicit, discouraged opt-in.
- Refuse every missing cell with no policy. Rejected: NaNs are common, and SAW has a sound available-case form, so a blanket refusal would throw away a valid analysis and the legitimate "treat a non-run as worst" decision.
- Available-case as the default. Rejected: it silently compares tools on different metric supports, which is exactly the kind of methodological choice the user must make explicitly.
- A coverage-aware Friedman (Skillings-Mack) now. Deferred: useful but a larger piece; the CD test refuses missing cells and points to the complete-case block in the meantime.

## References

- [Missing data in benchmark scores explanation](../explanations/missing-data.md)
- [ADR 0008 (mcda-aggregation-set)](0008-mcda-aggregation-set.md) for the five aggregations and the pymcdm wrapping.
- Skillings JH, Mack GA. On the use of a Friedman-type statistic in balanced and unbalanced block designs. Technometrics 1981, 23:171-177. The missing-data generalization of the Friedman test, noted as future work.
- Smith JE. Characterizing computer performance with a single number. Communications of the ACM 1988, 31:1202-1206. The basis for the available-case dataset-axis summary rules.
