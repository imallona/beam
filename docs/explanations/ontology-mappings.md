# Ontology mappings on metric cards

Every metric card under `src/beam/metrics/<id>/v1.yaml` carries an optional `mappings:` block that cross-references the metric to external ontologies and registries. This is the formalization the schema reserved from day one. From v1.0, the block is filled in on every card where a precise term exists upstream, and the gaps are documented in place.

## Ontologies in use

STATO, the Statistics Ontology (https://stato-ontology.org), is the main target. It is the only OBO Foundry ontology dedicated to statistical concepts: estimators, test statistics, distributions, study designs. When beam can write `mappings.stato: http://purl.obolibrary.org/obo/STATO_NNNNNNN` for a card, the metric is anchored to a stable external identifier that downstream tools can resolve without parsing beam's free-form prose.

UO, the Units of Measurement Ontology (http://purl.obolibrary.org/obo/uo.owl), covers SI base and derived units, prefixes, and common compound units. The unit-bearing cards use UO: runtime in seconds, peak memory in bytes, speed in kilometer per hour, co2 in grams. UO does not carry monetary units, so the toy `cost` card is left gapped on purpose.

OBI, the Ontology for Biomedical Investigations (https://obi-ontology.org), supplies the data-producing assay context for the scIB-family metrics. The scIB scores apply to single-cell RNA sequencing data; `mappings.obi: http://purl.obolibrary.org/obo/OBI_0002631` records that assay class on each scIB card. OBI also carries some statistical method terms that STATO is missing; pcr uses `OBI_0200104` (principal component regression) for that reason.

HuggingFace evaluate is a metric card registry rather than an ontology. Five of beam's cards have a direct counterpart in the HF registry (accuracy, F1, SMAPE, MASE, Spearman correlation) and the cross-reference is recorded as `mappings.huggingface_evaluate: <URL of HF card directory>`. The HF cards are not stable IRIs but their URLs are stable enough for the cross-reference to be useful; beam takes no dependency on the HF library.

## How to fill in `mappings` on a new card

1. Query the EBI Ontology Lookup Service (OLS) for the metric name in STATO first, then UO, then OBI. The OLS search endpoint is `https://www.ebi.ac.uk/ols4/api/search?q=<query>&ontology=<slug>`. The helper script `scripts/ols_query.py` does this in bulk for the registry; copy and adapt it for a new card.
2. Verify each candidate IRI by fetching it directly: `https://www.ebi.ac.uk/ols4/api/ontologies/<slug>/terms/<double-url-encoded-iri>`. Check that the label matches the metric and that `is_obsolete` is false. The helper `scripts/ols_verify.py` runs this check.
3. Write the full IRI into the card under `mappings:`. Use `http://purl.obolibrary.org/obo/STATO_NNNNNNN` (and similar) form, not short CURIEs. The schema validates the value as a URI string.
4. If no term exists, leave `mappings.stato` (or the equivalent key) absent and add a one-line YAML comment below the mappings block explaining the gap. Do not mint a beam-private IRI. Open an upstream issue against the relevant ontology tracker when the gap is one beam cares about for the long run; STATO accepts proposals via https://github.com/ISA-tools/stato/issues.
5. Re-run the test suite: `.venv/bin/python -m pytest tests/test_schema.py -q`. The card validates against the schema whatever mapping keys it carries.
6. Regenerate the OWL artefact: `python -m beam.owl.generate`. The script reads every card, builds a graph with each card as a `beam:Metric` instance plus its STATO parent when mapped, and writes `docs/beam.owl.ttl`.

## Per-card coverage

| metric_id | stato | uo | obi | huggingface_evaluate |
| --- | --- | --- | --- | --- |
| accuracy | STATO_0000415 | not in uo | not in obi | metrics/accuracy |
| ari | STATO_0000593 | not in uo | not in obi | not in hf |
| asw_batch | not in stato | not in uo | OBI_0002631 | not in hf |
| asw_label | not in stato | not in uo | OBI_0002631 | not in hf |
| calibration_slope | STATO_0000687 | not in uo | not in obi | not in hf |
| cell_cycle_conservation | not in stato | not in uo | OBI_0002631 | not in hf |
| clisi | not in stato | not in uo | OBI_0002631 | not in hf |
| co2 | not in stato | UO_0000021 | not in obi | not in hf |
| correlation | STATO_0000201 | not in uo | not in obi | metrics/spearmanr |
| cost | not in stato | not in uo | not in obi | not in hf |
| f1_score | STATO_0000628 | not in uo | not in obi | metrics/f1 |
| graph_connectivity | not in stato | not in uo | OBI_0002631 | not in hf |
| hvg_overlap | not in stato | not in uo | OBI_0002631 | not in hf |
| ilisi | not in stato | not in uo | OBI_0002631 | not in hf |
| isolated_label_asw | not in stato | not in uo | OBI_0002631 | not in hf |
| isolated_label_f1 | STATO_0000628 | not in uo | OBI_0002631 | not in hf |
| kbet | not in stato | not in uo | OBI_0002631 | not in hf |
| mase | not in stato | not in uo | not in obi | metrics/mase |
| nclust_deviation | not in stato | not in uo | not in obi | not in hf |
| nmi | not in stato | not in uo | not in obi | not in hf |
| pcr | not in stato | not in uo | OBI_0200104 | not in hf |
| peak_memory | not in stato | UO_0000233 | not in obi | not in hf |
| runtime | not in stato | UO_0000010 | not in obi | not in hf |
| shannon_entropy_diff | not in stato | not in uo | not in obi | not in hf |
| silhouette | not in stato | not in uo | not in obi | not in hf |
| smape | not in stato | not in uo | not in obi | metrics/smape |
| speed | not in stato | UO_0010008 | not in obi | not in hf |

Summary as of 2026-05-28: STATO covers 6 of 27 cards (ari, accuracy, f1_score, isolated_label_f1, calibration_slope, correlation). UO covers 4 of 27 (runtime, peak_memory, speed, co2). OBI covers 11 of 27 (the scIB family with OBI_0002631 plus pcr with OBI_0200104). HuggingFace evaluate covers 5 of 27 (accuracy, f1_score, smape, mase, correlation).

## Proposed-upstream gaps

The following cards have no STATO mapping today and would benefit from a STATO term on a later release. Each is honest; none should be filled by minting a beam-private IRI.

- nmi: STATO carries AIC, BIC, DIC information criteria but not the partition-similarity normalized mutual information of Strehl and Ghosh 2002. A STATO term for partition-similarity mutual information would be the natural fix.
- silhouette and the four scIB silhouette variants (asw_batch, asw_label, isolated_label_asw, isolated_label_f1's silhouette parent): no STATO term for the Rousseeuw 1987 silhouette coefficient. A STATO term for the silhouette coefficient would cover the family.
- kbet: no STATO term for the Buttner et al. 2019 batch-effect test.
- clisi and ilisi: no STATO term for the Korsunsky et al. 2019 local inverse Simpson index.
- shannon_entropy_diff: no STATO term for Shannon entropy. A STATO term for the Shannon entropy of a partition would cover this card and any future entropy-based metric.
- nclust_deviation, hvg_overlap, graph_connectivity, cell_cycle_conservation: scIB-specific scores; a STATO term for each is unlikely but not impossible.
- smape, mase: forecasting-accuracy metrics; STATO carries percentage and statistical error parents but not the M4-standard variants. A STATO term for each would be a clean addition.
- runtime, peak_memory: operational measurands rather than statistical estimators; the UO mapping is the right anchor and a STATO mapping is not expected.
- cost, speed, co2: toy transportation metrics; the UO unit mapping is the right anchor where applicable.

## How the OWL is regenerated

`src/beam/owl/generate.py` reads every card under `src/beam/metrics/<id>/v*.yaml`, builds an rdflib graph, and writes `docs/beam.owl.ttl`. Each card becomes a `beam:Metric` instance. A card with `mappings.stato` is additionally asserted as an instance of the STATO class (via `rdf:type` and `owl:sameAs`). UO, OBI, QUDT, OM2 and HuggingFace mappings are recorded as `rdfs:seeAlso`. The graph is small (around 140 triples) and parses with rdflib without warnings.

To regenerate after editing a card:

```
.venv/bin/python -m beam.owl.generate
```

The artefact is deposited on Zenodo per release for a permanent identifier. The OWL is reproducible from the cards plus the schema, so the Zenodo deposit is a versioned snapshot rather than a separately maintained file.

## The SKOS controlled vocabulary

The cards draw four fields from closed enumerations: polarity, scale_type, allowed_transformations and comparability.recommended_normalization. `src/beam/owl/skos.py` publishes those enumerations as SKOS concept schemes in `docs/beam.skos.ttl`. Each allowed value becomes one `skos:Concept` with a prefLabel and a definition. A `skos:broader` edge records where one value specializes another: the Stevens scale ladder from nominal to ratio, and the normalizations that are special cases of an affine transform. The enum values are read from the JSON Schema, so a value no card uses yet still gets a concept. The definitions are kept in the generator, taken from the measurement-theory and normalization-and-scales essays. Regenerate with `python -m beam.owl.skos`.

The upstream STATO proposals for the gapped metrics are drafted in [stato-term-proposals.md](stato-term-proposals.md).
