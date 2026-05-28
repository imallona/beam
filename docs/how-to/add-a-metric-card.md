# Add a new metric card

Each metric card is one YAML file under `src/beam/metrics/<id>/v1.yaml`. The card carries the metadata the pipeline needs to normalize, weight and aggregate the metric correctly: polarity (higher or lower better), scale type, range, allowed transformations, a recommended normalization, and the ontology mappings (STATO, UO, OBI, HuggingFace evaluate) where an external term exists.

This recipe walks through adding a card for a new metric called `recall_at_k`.

## 1. Pick the id and the version

The id is a short lowercase string that becomes the column name in score CSVs. The version is a simple `v1`, `v2` and so on. Make a folder:

```
mkdir -p src/beam/metrics/recall_at_k
```

## 2. Write `v1.yaml`

Use an existing card as a template. The seed card `accuracy/v1.yaml` is a short example for a classification metric. Copy and edit:

```yaml
id: recall_at_k
version: v1
name: Recall at k
description: >
  Fraction of the relevant items that appear in the top k of a ranked
  retrieval list, averaged over queries.
citations:
- text: Manning, Raghavan and Schuetze. Introduction to Information Retrieval.
    Cambridge University Press 2008.
  isbn: 9780521865715
metric_kind: classification
measurand: retrieval recall
task: information retrieval
input_dtype: ranking
output_shape: scalar
scale_type: ratio
polarity: higher_is_better
range:
  lower: 0
  upper: 1
  closed_lower: true
  closed_upper: true
allowed_transformations:
- affine
- log
semantics:
  score_of_random_baseline: 0
comparability:
  recommended_normalization: min_max
  recommended_aggregation_across_datasets: arithmetic_mean
implementations:
- name: scikit-learn
  version: ">=1.3"
  package: scikit-learn
  function: sklearn.metrics.top_k_accuracy_score
  language: python
  license: BSD-3-Clause
  url: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.top_k_accuracy_score.html
mappings:
  huggingface_evaluate: https://github.com/huggingface/evaluate/tree/main/metrics/recall
provenance:
  author: Your Name
  contact: you@example.org
  created: 2026-05-28
  license: CC-BY-4.0
```

## 3. Validate

```
.venv/bin/python -m pytest tests/test_schema.py -q
```

The schema check runs against every card in the registry. A missing required field, a polarity that does not match the polarity enum, or a range that is inverted (lower > upper) raises a clear error.

## 4. Optionally add a STATO or UO mapping

If your metric has a term in the Statistics Ontology, the Units of Measurement Ontology, the Ontology for Biomedical Investigations, or the HuggingFace evaluate catalogue, add the full IRI under `mappings`. The helper script `scripts/ols_query.py` searches OLS for candidate IRIs; use `scripts/ols_verify.py` to confirm a candidate is the right term and is not obsolete. Do not invent IRIs.

The cards-and-pipeline page lists which fields the pipeline reads and which are reserved for documentation. See [../explanations/cards-and-pipeline.md](../explanations/cards-and-pipeline.md).

## 5. Regenerate the OWL release artefact

```
.venv/bin/python -m beam.owl.generate
```

This rewrites `docs/beam.owl.ttl` from the cards plus the schema. The new card now appears as an instance under its STATO parent (if mapped) or under the beam-private metric class (if not yet mapped).

## 6. Add a unit test for the metric (optional)

If your card declares one or more `implementations`, write a small example under `tests/` that confirms the implementation produces the expected output on a documented input.
