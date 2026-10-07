# Ontology mappings on metric cards

Each metric card has an optional `mappings:` block that links the metric to external ontologies and registries. It is filled where an upstream term exists.

## Ontologies

- STATO, the Statistics Ontology (https://stato-ontology.org): estimators, test statistics, distributions, study designs. `mappings.stato: http://purl.obolibrary.org/obo/STATO_NNNNNNN`.
- UO, the Units of Measurement Ontology (http://purl.obolibrary.org/obo/uo.owl): runtime in seconds, peak memory in bytes, speed in kilometer per hour, co2 in grams. UO has no monetary units, so `cost` has no mapping.
- OBI, the Ontology for Biomedical Investigations (https://obi-ontology.org): the assay of the scIB metrics, single-cell RNA sequencing (`OBI_0002631`), and principal component regression for pcr (`OBI_0200104`).
- HuggingFace evaluate, a metric card registry: `mappings.huggingface_evaluate` has the URL of the card directory for accuracy, F1, SMAPE, MASE and Spearman correlation. beam does not depend on the library.

## Mapping a new card

1. Search the EBI Ontology Lookup Service (OLS) in STATO, then UO, then OBI: `https://www.ebi.ac.uk/ols4/api/search?q=<query>&ontology=<slug>`. `scripts/ols_query.py` does this for the registry.
2. Fetch each candidate, `https://www.ebi.ac.uk/ols4/api/ontologies/<slug>/terms/<double-url-encoded-iri>`, and check the label and that `is_obsolete` is false. `scripts/ols_verify.py` runs this check.
3. Write the full IRI under `mappings:`. The schema types each value as a URI.
4. Without a term, leave the key absent and add a one-line YAML comment below the block. beam-private IRIs are not minted. STATO takes proposals at https://github.com/ISA-tools/stato/issues.
5. Run `python -m pytest tests/test_schema.py -q`.
6. Regenerate the OWL: `python -m beam.owl.generate`.

## Coverage

| metric_id | stato | uo | obi | huggingface_evaluate |
| --- | --- | --- | --- | --- |
| accuracy | STATO_0000415 | not in uo | not in obi | metrics/accuracy |
| ari | STATO_0000593 | not in uo | not in obi | not in hf |
| asw_batch | not in stato | not in uo | OBI_0002631 | not in hf |
| asw_label | not in stato | not in uo | OBI_0002631 | not in hf |
| calibration_slope | STATO_0000687 | not in uo | not in obi | not in hf |
| cell_cycle_conservation | not in stato | not in uo | OBI_0002631 | not in hf |
| cell_type_annotation_agreement | not in stato | not in uo | not in obi | not in hf |
| cell_type_annotation_full_match_rate | not in stato | not in uo | not in obi | not in hf |
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

Summary: STATO covers 6 of 29 cards (ari, accuracy, f1_score, isolated_label_f1, calibration_slope, correlation). UO covers 4 of 29 (runtime, peak_memory, speed, co2). OBI covers 11 of 29 (the scIB family with OBI_0002631 plus pcr with OBI_0200104). HuggingFace evaluate covers 5 of 29 (accuracy, f1_score, smape, mase, correlation).

## OWL

`src/beam/owl/generate.py` reads the cards, builds an rdflib graph, and writes `docs/beam.owl.ttl`. Each card is a `beam:Metric` instance. A card with `mappings.stato` is also an instance of the STATO class (`rdf:type` and `owl:sameAs`). UO, OBI, QUDT, OM2 and HuggingFace mappings are `rdfs:seeAlso`.

## SKOS vocabulary

Four card fields are closed enumerations: polarity, scale_type, allowed_transformations and comparability.recommended_normalization. `src/beam/owl/skos.py` writes them as SKOS concept schemes to `docs/beam.skos.ttl`, one `skos:Concept` per value with a prefLabel and a definition. `skos:broader` links the Stevens scales from nominal to ratio, and the normalizations that are special cases of an affine transform. The values are read from the JSON Schema. Regenerate with `python -m beam.owl.skos`.

## Draft STATO proposals

Metrics without a STATO term, with the parent class and reference for an issue at the STATO tracker. Runtime, peak_memory and the [transportation metrics](../../examples/transportation/transportation.qmd) (cost, speed, co2) are out of STATO scope.

- Normalized mutual information (nmi). Mutual information between two partitions divided by a function of their entropies, in the unit interval. Parent: measure of clustering agreement, sibling of the adjusted Rand index (STATO_0000593). Strehl and Ghosh 2002, JMLR 3:583-617.
- Silhouette coefficient (silhouette, asw_batch, asw_label, isolated_label_asw). Mean over points of the difference between the mean nearest-other-cluster distance and the mean within-cluster distance, divided by the larger. Parent: cluster validity index. Rousseeuw 1987, DOI [10.1016/0377-0427(87)90125-7](https://doi.org/10.1016/0377-0427%2887%2990125-7).
- k-nearest-neighbour batch-effect test statistic (kbet). Chi-squared comparison of the batch composition of local k-neighbourhoods with the global composition; the rejection rate is reported. Parent: test statistic. Buttner et al. 2019, DOI [10.1038/s41592-018-0254-1](https://doi.org/10.1038/s41592-018-0254-1).
- Local inverse Simpson index (clisi, ilisi). Inverse Simpson index of the label or batch composition in a perplexity-weighted neighbourhood. Parent: diversity index. Korsunsky et al. 2019, DOI [10.1038/s41592-019-0619-0](https://doi.org/10.1038/s41592-019-0619-0).
- Shannon entropy of a partition (shannon_entropy_diff). Parent: information-theoretic measure. Shannon 1948, DOI [10.1002/j.1538-7305.1948.tb01338.x](https://doi.org/10.1002/j.1538-7305.1948.tb01338.x).
- Symmetric mean absolute percentage error (smape). Mean over horizons of the absolute forecast error divided by the average of the absolute actual and forecast values, in percent. Parent: measure of forecast error. Makridakis, Spiliotis and Assimakopoulos 2020, DOI [10.1016/j.ijforecast.2019.04.014](https://doi.org/10.1016/j.ijforecast.2019.04.014).
- Mean absolute scaled error (mase). Mean absolute forecast error divided by the in-sample mean absolute error of a naive one-step forecast. Parent: measure of forecast error. Hyndman and Koehler 2006, DOI [10.1016/j.ijforecast.2006.03.001](https://doi.org/10.1016/j.ijforecast.2006.03.001).
