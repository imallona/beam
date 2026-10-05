# Add a new metric card

Each metric card is one YAML file under `src/beam/metrics/<id>/v1.yaml`. The card has the metadata the pipeline uses to normalize, weight and aggregate the metric: [polarity](../explanations/measurement-theory.md) (higher or lower better), scale type, range, allowed transformations, a [recommended normalization](../explanations/normalization-and-scales.md), and the [ontology mappings](../explanations/ontology-mappings.md) (STATO, UO, OBI, HuggingFace evaluate) where an external term exists.

## 1. Pick the id and the version

The id is a short lowercase string that becomes the column name in score CSVs. The version is a simple `v1`, `v2` and so on:

```
mkdir -p src/beam/metrics/recall_at_k
```

## 2. Write `v1.yaml`

A card for a retrieval metric, with the required fields only. `accuracy/v1.yaml` shows the optional ones:

```yaml
id: recall_at_k
version: v1
name: Recall at k
description: |
  Fraction of the relevant items that appear in the top k of a ranked
  retrieval list, averaged over queries.
citations:
  - text: Manning, Raghavan and Schuetze. Introduction to Information Retrieval. Cambridge University Press 2008.
metric_kind: derived
measurand: fraction of relevant items retrieved in the top k
task:
  - information_retrieval
requires_ground_truth: true
ground_truth:
  description: relevant items per query
  shape: set
  dtype: item_id
inputs:
  - role: ranked_items
    shape: vector
    dtype: item_id
  - role: relevant_items
    shape: set
    dtype: item_id
output:
  shape: scalar
  dtype: float
semantics:
  scale_type: ratio
  range:
    lower: 0
    upper: 1
    lower_inclusive: true
    upper_inclusive: true
  polarity: higher_is_better
  monotonic: true
  meaningful_zero: true
  allowed_transformations:
    - affine
    - rank
comparability:
  comparable_within:
    - same_dataset
  recommended_aggregation_across_datasets: arithmetic_mean
  recommended_normalization: min_max
implementations:
  - name: torchmetrics
    language: python
    package: torchmetrics
    function: torchmetrics.retrieval.RetrievalRecall
    license: Apache-2.0
examples:
  - description: one of two relevant items in the top 2
    inputs:
      ranked_items: [a, b, c, d]
      relevant_items: [a, d]
      k: 2
    expected_output: 0.5
    tolerance: 1.0e-12
provenance:
  author: Your Name
  contact: you@example.org
  created: "2026-05-28"
  license: CC-BY-4.0
```

## 3. Validate

```
.venv/bin/python -m pytest tests/test_schema.py -q
```

The schema check runs against every card in the registry. A missing required field, a polarity that does not match the polarity enum, or an inverted range (lower > upper) raises an error.

## 4. Optionally add a STATO or UO mapping

A metric with a term in the Statistics Ontology, the Units of Measurement Ontology, the Ontology for Biomedical Investigations, or the HuggingFace evaluate catalogue takes the full IRI under `mappings`. `scripts/ols_query.py` searches OLS for candidate IRIs, and `scripts/ols_verify.py` confirms a candidate is the right term and not obsolete. Only existing IRIs are used.

The cards-and-pipeline page lists which fields the pipeline reads and which are reserved for documentation. See [../explanations/cards-and-pipeline.qmd](../explanations/cards-and-pipeline.qmd).

## 5. Regenerate the OWL release artefact

```
.venv/bin/python -m beam.owl.generate
```

This rewrites `docs/beam.owl.ttl` from the cards plus the schema. The new card now appears as an instance under its STATO parent (if mapped) or under the beam-private metric class (if not yet mapped).

## 6. Add a unit test for the metric (optional)

A card that declares `implementations` warrants a small example under `tests/` confirming the implementation produces the expected output on a documented input.
