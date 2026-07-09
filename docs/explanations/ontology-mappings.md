# Ontology mappings on metric cards

Every metric card under `src/beam/metrics/<id>/v1.yaml` carries an optional `mappings:` block that cross-references the metric to external ontologies and registries. This is the formalization the schema reserved from day one. From v1.0, the block is filled in on every card where a precise term exists upstream, and the gaps are documented in place.

## Ontologies in use

- STATO, the Statistics Ontology (https://stato-ontology.org), is the main target. It is the only OBO Foundry ontology dedicated to statistical concepts: estimators, test statistics, distributions, study designs. When beam can write `mappings.stato: http://purl.obolibrary.org/obo/STATO_NNNNNNN` for a card, the metric is anchored to a stable external identifier that downstream tools can resolve without parsing beam's free-form prose.
- UO, the Units of Measurement Ontology (http://purl.obolibrary.org/obo/uo.owl), covers SI base and derived units, prefixes, and common compound units. The unit-bearing cards use UO: runtime in seconds, peak memory in bytes, speed in kilometer per hour, co2 in grams. UO does not carry monetary units, so the toy `cost` card is left gapped on purpose.
- OBI, the Ontology for Biomedical Investigations (https://obi-ontology.org), supplies the data-producing assay context for the scIB-family metrics. The scIB scores apply to single-cell RNA sequencing data; `mappings.obi: http://purl.obolibrary.org/obo/OBI_0002631` records that assay class on each scIB card. OBI also includes some statistical method terms that STATO is missing; pcr uses `OBI_0200104` (principal component regression) for that reason.
- HuggingFace evaluate is a metric card registry rather than an ontology. Five of beam's cards have a direct counterpart in the HF registry (accuracy, F1, symmetric mean absolute percentage error (SMAPE), mean absolute scaled error (MASE), Spearman correlation) and the cross-reference is recorded as `mappings.huggingface_evaluate: <URL of HF card directory>`. The HF cards are not stable IRIs but their URLs are stable enough for the cross-reference to be useful; beam takes no dependency on the HF library.

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

## How the OWL is regenerated

`src/beam/owl/generate.py` reads every card under `src/beam/metrics/<id>/v*.yaml`, builds an rdflib graph, and writes `docs/beam.owl.ttl`. Each card becomes a `beam:Metric` instance. A card with `mappings.stato` is additionally asserted as an instance of the STATO class (via `rdf:type` and `owl:sameAs`). UO, OBI, QUDT, OM2 and HuggingFace mappings are recorded as `rdfs:seeAlso`. The graph is small (around 140 triples) and parses with rdflib without warnings.

To regenerate after editing a card:

```
.venv/bin/python -m beam.owl.generate
```

The artefact is deposited on Zenodo per release for a permanent identifier. The OWL is reproducible from the cards plus the schema, so the Zenodo deposit is a versioned snapshot rather than a separately maintained file.

## The SKOS controlled vocabulary

The cards draw four fields from closed enumerations: polarity, scale_type, allowed_transformations and comparability.recommended_normalization. `src/beam/owl/skos.py` publishes those enumerations as SKOS concept schemes in `docs/beam.skos.ttl`. Each allowed value becomes one `skos:Concept` with a prefLabel and a definition. A `skos:broader` edge records where one value specializes another: the Stevens scale ladder from nominal to ratio, and the normalizations that are special cases of an affine transform. The enum values are read from the JSON Schema, so a value no card uses yet still gets a concept. The definitions are kept in the generator, taken from the [measurement-theory](measurement-theory.md) and [normalization-and-scales](normalization-and-scales.md) essays. Regenerate with `python -m beam.owl.skos`.

## Draft STATO proposals

The coverage table above lists the metrics with no STATO term. The proposals below are drafts to file against the STATO tracker (https://github.com/ISA-tools/stato/issues) rather than fill with a beam-private IRI. Other measurands (runtime, peak_memory) and the [transportation metrics](../../examples/transportation/transportation.qmd) (cost, speed, co2) are out of STATO scope.

To file one, open an issue with the label, the definition, and the parent class named below, and attach the primary reference. When STATO assigns an IRI, write it into the matching card under `mappings.stato`, regenerate the OWL with `python -m beam.owl.generate`, and update the coverage table above.

### normalized mutual information (partition similarity)

- Definition: a clustering-agreement measure equal to the mutual information between two partitions divided by a normalizing function of their entropies, valued in the unit interval.
- Parent: a measure of clustering agreement, sibling of the adjusted Rand index (STATO_0000593, already mapped on the ari card).
- beam card: nmi.
- Reference: Strehl and Ghosh 2002, Cluster ensembles, JMLR 3:583-617.

### silhouette coefficient

- Definition: a cluster-validity measure equal to the mean over points of the difference between the mean nearest-other-cluster distance and the mean within-cluster distance, normalized by the larger of the two.
- Parent: cluster validity index, a kind of summary statistic.
- beam cards: silhouette, and as children the scIB silhouette variants asw_batch, asw_label and isolated_label_asw, which apply the same coefficient over a batch or a label assignment. One upstream silhouette term covers the family; the variant stays recorded on the beam card.
- Reference: Rousseeuw 1987, Silhouettes, Journal of Computational and Applied Mathematics 20:53-65, DOI [10.1016/0377-0427(87)90125-7](https://doi.org/10.1016/0377-0427%2887%2990125-7).

### k-nearest-neighbour batch-effect test statistic

- Definition: a batch-mixing test that compares, over local k-neighbourhoods, the observed batch-label composition against the global composition by a chi-squared statistic, with the rejection rate reported.
- Parent: test statistic, a kind of chi-squared based statistic.
- beam card: kbet.
- Reference: Buttner, Miao, Wolf, Teichmann and Theis 2019, A test metric for assessing single-cell RNA-seq batch correction, Nature Methods 16:43-49, DOI [10.1038/s41592-018-0254-1](https://doi.org/10.1038/s41592-018-0254-1).

### local inverse Simpson index

- Definition: a local-neighbourhood diversity measure equal to the inverse Simpson index of the label composition (cLISI) or the batch composition (iLISI) within a perplexity-weighted neighbourhood.
- Parent: diversity index, a kind of summary statistic.
- beam cards: clisi, ilisi.
- Reference: Korsunsky et al. 2019, Fast, sensitive and accurate integration of single-cell data with Harmony, Nature Methods 16:1289-1296, DOI [10.1038/s41592-019-0619-0](https://doi.org/10.1038/s41592-019-0619-0).

### Shannon entropy of a partition

- Definition: the Shannon entropy, in nats or bits, of the label distribution of a partition. A STATO term at this level would cover the difference reported by beam's card and any future entropy-based metric.
- Parent: information-theoretic measure, a kind of summary statistic.
- beam card: shannon_entropy_diff.
- Reference: Shannon 1948, A mathematical theory of communication, Bell System Technical Journal 27:379-423, DOI [10.1002/j.1538-7305.1948.tb01338.x](https://doi.org/10.1002/j.1538-7305.1948.tb01338.x).

### symmetric mean absolute percentage error

- Definition: a forecasting-accuracy error equal to the mean over horizons of the absolute forecast error divided by the average of the absolute actual and forecast values, in percent.
- Parent: a measure of forecast error, a kind of percentage.
- beam card: smape.
- Reference: Makridakis, Spiliotis and Assimakopoulos 2020, The M4 Competition, International Journal of Forecasting 36:54-74, DOI [10.1016/j.ijforecast.2019.04.014](https://doi.org/10.1016/j.ijforecast.2019.04.014).

### mean absolute scaled error

- Definition: a forecasting-accuracy error equal to the mean absolute forecast error scaled by the in-sample mean absolute error of a naive one-step forecast.
- Parent: a measure of forecast error, a kind of summary statistic.
- beam card: mase.
- Reference: Hyndman and Koehler 2006, Another look at measures of forecast accuracy, International Journal of Forecasting 22:679-688, DOI [10.1016/j.ijforecast.2006.03.001](https://doi.org/10.1016/j.ijforecast.2006.03.001).
