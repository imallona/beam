# Card and data consistency

A metric card declares the metric value range, a baseline of what is obtainable by chance, an ideal target, and a noise floor. The [multi-criteria decision analysis (MCDA) pipeline](cards-and-pipeline.qmd) reads each of these: the range bounds the [normalization](normalization-and-scales.md), the baseline anchors `baseline_relative` scaling and the beats-chance check, the target sets `target_relative` scaling, and the [noise floor](reference-levels.md) sets which method differences are interpretable.

[`beam.mcda.card_data_consistency`](../reference/card_data_consistency.qmd) reads the raw scores against the card values, before any normalization, and reports where they disagree. `validate.py` checks the aggregation is licit for the declared [scale type](measurement-theory.md); this audit checks the data against the declared values.

A recurring failure is a unit mismatch. A metric defined on the `[0, 1]` fraction scale is reported as a percentage, so the column runs to 100 against a card that declares the `[0, 1]` range. The column is still numeric and still interval, so it passes the schema validation and the scale-versus-method check. It then distorts the min-max normalization for that metric and the [weighting](weighting-schemes.md) that is based on it. The audit detects this on the raw scores and reports the metric, the number of tools outside the range, and the worst value.

## Checks

The audit splits its findings by severity. A violation is a contradiction between the card and the data:

- `out_of_range`: an observed score falls below the declared lower bound or above the upper bound.
- `baseline_out_of_range`: the declared chance baseline lies outside the declared range. A `target_value` metric has no chance level, so its baseline, if any, is not checked.
- `target_out_of_range`: the declared target lies outside the declared range.
- `nonpositive_noise_floor`: the declared noise floor is zero or negative, which is not a width in native units.
- `malformed_range`: the declared lower bound exceeds the upper bound.

A note depends on this score matrix and is not necessarily a card error:

- `degenerate`: the metric is constant across the observed tools, so it cannot separate the tools here.
- `noise_floor_exceeds_spread`: a positive noise floor is at least as wide as the whole observed spread, so the metric separates no pair of tools on this data.
- `no_observations`: every cell of the metric is missing.

The `ok` flag is true when there are no violations. Notes do not change it and are listed.

## Redundant checks

[`beam.mcda.normalize`](../reference/normalize.qmd) also has a narrow guard: it raises when a column's minimum or maximum falls outside the declared bounds. That guard fires inside the ranking call, stops at the first offending column, reports a column index without the metric id, and checks only the range. `card_data_consistency` is the full standalone audit. It reads all metrics in one pass, names each one, grades the findings, and adds the baseline, target, noise-floor and degeneracy checks absent from the normalization guard.

## Running

`beam.rank` runs the audit after the ranking and attaches the report to `RunResult.card_consistency`; the HTML report has a "Card and data consistency" section when the audit has findings. A score outside the declared range makes the normalization step raise an error before the audit runs, so `beam.rank` never reports a range violation. To check the ranges, call the audit directly on the scores before ranking:

```python
from beam.mcda import card_data_consistency, registry_context

context = registry_context(metric_ids, "saw")
report = card_data_consistency(
    raw_scores,  # native-unit tool-by-metric matrix
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

This audit does not confirm the metric was computed correctly; implementation drift is the subject of the `implementations.tested_against` card field.
