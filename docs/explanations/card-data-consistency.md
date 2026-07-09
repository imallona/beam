# Card and data consistency

A metric card declares the metric value range, a baseline of what is obtainable by chance, an ideal target, and a noise floor. The [multi-criteria decision analysis (MCDA) pipeline](cards-and-pipeline.qmd) reads each of these: the range bounds the [normalization](normalization-and-scales.md), the baseline anchors `baseline_relative` scaling and the beats-chance check, the target drives `target_relative` scaling, and the [noise floor](reference-levels.md) sets which method differences are interpretable.

[`beam.mcda.card_data_consistency`](../reference/card_data_consistency.qmd) reads the raw scores against the card values, before any normalization, and reports where they disagree. `validate.py` checks the aggregation is licit for the declared [scale type](measurement-theory.md); this audit checks the data against the declared values.

A recurring failure is a unit mismatch. A metric defined on the `[0, 1]` fraction scale is reported as a percentage, so the column runs to 100 against a card that declares the `[0, 1]` range. The column is still numeric and still interval, so it passes the schema validation and the scale-versus-method check. It then distorts the min-max normalization for that metric and the [weighting](weighting-schemes.md) that rests on it. The audit catches this on the raw scores: it names the metric, counts how many tools fall outside the range, and gives the worst value.

## Checks

The audit splits its findings by severity. A violation is a hard card-or-data contradiction that needs fixing:

- `out_of_range`: an observed score falls below the declared lower bound or above the upper bound.
- `baseline_out_of_range`: the declared chance baseline lies outside the declared range. A `target_value` metric has no chance level, so its baseline, if any, is not checked.
- `target_out_of_range`: the declared target lies outside the declared range.
- `nonpositive_noise_floor`: the declared noise floor is zero or negative, which is not a width in native units.
- `malformed_range`: the declared lower bound exceeds the upper bound.

A note is a data-dependent observation, true of this particular score matrix but not necessarily a card error:

- `degenerate`: the metric is constant across the observed tools, so it carries no ranking signal here.
- `noise_floor_exceeds_spread`: a positive noise floor is at least as wide as the whole observed spread, so the metric separates no pair of tools on this data.
- `no_observations`: every cell of the metric is missing.

The `ok` flag is true when there are no violations. Notes do not clear it but are surfaced.

## Redundant checks

[`beam.mcda.normalize`](../reference/normalize.qmd) also has a narrow guard: it raises when a column's minimum or maximum falls outside the declared bounds. That guard fires inside the ranking call, stops at the first offending column, names a column index rather than the metric, and checks only the range. `card_data_consistency` is the full standalone audit. It reads all metrics in one pass, names each one, grades the findings, and adds the baseline, target, noise-floor, and degeneracy checks the normalization guard does not make.

## Running

`beam.rank` runs the audit on the ranked matrix and attaches the report to `RunResult.card_consistency`, and the HTML report draws a "Card and data consistency" section when the audit raises anything. At rank time a range violation is caught by the normalization guard first, so the headline use is the standalone call on the raw scores:

```python
from beam.mcda import card_data_consistency, registry_context

context = registry_context(metric_ids, "saw")
report = card_data_consistency(
    raw_scores,                 # native-unit tool-by-metric matrix
    context.polarity,
    context.bounds,
    baselines=context.baselines,
    targets=context.targets,
    noise_floors=context.noise_floors,
    metric_ids=metric_ids,
)
if not report.ok:
    for finding in report.violations:
        print(finding.message)
```

## Limits

This safeguard does not confirm the metric was computed correctly, which is the implementation-drift question the `implementations.tested_against` card field is meant to address.
