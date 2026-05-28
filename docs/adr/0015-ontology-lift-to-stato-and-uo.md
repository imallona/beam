# 0015 - Ontology lift to STATO, UO, OBI for the v1.0 cards

- Status: Accepted
- Date: 2026-05-28
- Deciders: Izaskun Mallona
- Supersedes: -
- Superseded by: -

## Context

beam is a metric formalization layer. The metric card schema reserves a `mappings:` block as an open dictionary of cross-references, with the intent that each card carry stable external identifiers for the statistical concept it measures, the unit it is expressed in, and the assay it applies to. Earlier internal notes scheduled this ontology lift for after the v1.0 release; on 2026-05-28 it was pulled forward into v1.0. The reasoning: shipping a CRAN-bound formalization layer whose cards have no external IRIs is shipping the binding before the book. The maintainer has working OWL and RDF skill, the schema reserves the slot already, and the change is additive: existing cards stay valid, the schema bumps a minor version, the R wrapper reads cards unchanged.

The 27 cards under `src/beam/metrics/<id>/v1.yaml` cover clustering (ari, nmi, silhouette, shannon_entropy_diff, nclust_deviation), classification (accuracy, f1_score, calibration_slope), forecasting (smape, mase), efficiency (runtime, peak_memory), single-cell integration (asw_batch, asw_label, isolated_label_asw, isolated_label_f1, kbet, ilisi, clisi, graph_connectivity, hvg_overlap, cell_cycle_conservation, pcr), spatial (correlation), and the toy transportation set (speed, cost, co2). STATO covers the statistical estimators; UO covers SI and derived units; OBI covers the assay context for the scIB-family scRNA-seq metrics. The first sweep was expected to land a clean external IRI on roughly half to two thirds of the 27 cards, with the rest honestly gapped.

## Decision

For each card, a sweep over the EBI Ontology Lookup Service (https://www.ebi.ac.uk/ols4) in three ontologies in priority order: STATO (primary), UO (units), OBI (assay context where applicable). Each candidate IRI is verified by a direct term fetch (label and obsolescence) before being written to a card.

- STATO is the primary target. Every card with a precise statistical concept in STATO carries `mappings.stato` as the full IRI `http://purl.obolibrary.org/obo/STATO_NNNNNNN`. Confirmed for ari (STATO_0000593), f1_score (STATO_0000628), accuracy (STATO_0000415), calibration_slope (STATO_0000687), correlation (STATO_0000201, Spearman's rank correlation matching the OpenProblems spatial card), and isolated_label_f1 (STATO_0000628, the F1 parent, plus the OBI assay term). The pcr card uses OBI_0200104 (principal component regression) because that method term lives in OBI, not STATO.
- UO carries the unit terms for runtime (UO_0000010, second), peak_memory (UO_0000233, byte), and speed (UO_0010008, kilometer per hour). co2 records UO_0000021 (gram) as the mass unit; UO has no compound g/km, so the per-distance dimension stays implicit in the measurand string. cost has no UO mapping because UO does not carry monetary units.
- OBI annotates the assay context for the scIB-family cards as OBI_0002631 (single-cell RNA sequencing assay). It is carried on asw_batch, asw_label, isolated_label_asw, isolated_label_f1, kbet, ilisi, clisi, graph_connectivity, hvg_overlap, and cell_cycle_conservation. The pcr card uses OBI_0200104 (principal component regression) instead, the precise method term in OBI.
- For cards where no STATO term exists, `mappings.stato` is absent and a comment below the mappings block documents the gap. beam mints no private IRIs. The honest gaps are nmi, silhouette and the silhouette-derived asw_batch and asw_label, the LISI family (clisi, ilisi), kbet, graph_connectivity, hvg_overlap, cell_cycle_conservation, shannon_entropy_diff, nclust_deviation, smape, mase, and the operational quantities runtime, peak_memory, speed, cost, co2. These are recorded in docs/explanations/ontology-mappings.md with a proposed-upstream note for the statistical ones (NMI, silhouette, kBET, LISI, Shannon entropy difference, MASE, SMAPE) that STATO could plausibly cover on a later release.
- HuggingFace evaluate cards are cross-referenced where the metric overlaps: accuracy, f1_score, smape, mase, correlation (spearmanr). These are recorded as `mappings.huggingface_evaluate` and point at the HF metric card directory URL.
- The JSON Schema bumps to version 1.1 (description string note; no breaking change). `mappings.stato`, `mappings.uo`, `mappings.obi`, `mappings.qudt`, `mappings.om2`, `mappings.huggingface_evaluate` are enumerated as typed URI string properties. `additionalProperties: true` stays so existing free-form keys and any future key validate without a schema bump.
- An OWL release artefact lives at `docs/beam.owl.ttl`. Each card becomes a beam:Metric instance; cards with a STATO mapping are also asserted as an instance of the STATO class via owl:sameAs; UO, OBI and HF cross-references are recorded as rdfs:seeAlso. The Turtle is reproducible from the cards via `python -m beam.owl.generate`. Turtle is the chosen serialization because it is the most readable form when a senior reviewer wants to eyeball the asserted triples; the file parses with rdflib without warnings.
- rdflib is added under the dev optional dependency. It is not a runtime path; the OWL is a release artefact deposited on Zenodo per release, and the CRAN-bound R wrapper does not load it.

## Consequences

- Every metric card now carries a stable external identifier where one exists, so a downstream user can resolve the statistical concept beyond the human-readable name. The MCDA layer still reads the cards on `polarity` only; the new fields are for users, reviewers, and the manuscript's standards-alignment paragraph.
- Honest gaps stay visible. A card without a STATO mapping carries an inline comment explaining why and pointing to docs/explanations/ontology-mappings.md. No private beam:Metric subclass is minted; the OWL keeps the gap explicit.
- Schema bumps are additive. The 1.0 to 1.1 change adds typed enumeration for known keys and keeps additionalProperties open, so a card that uses a future key like `mappings.edam` validates without a schema release.
- The OWL artefact is reproducible from the cards plus the schema in one short script. A Zenodo deposit per release keeps every snapshot resolvable.
- The cross-reference to HuggingFace evaluate documents the standards overlap on five metrics (accuracy, F1, SMAPE, MASE, Spearman) without taking a dependency on the HF library.

## Alternatives considered

- Defer the ontology lift to a post-v1.0 release (the original plan). Rejected: the OWL and RDF skill is in-house, the schema reserves the slot, and v1.0 is the right moment to pin external identifiers before the CRAN release.
- Mint beam-private IRIs for the gap concepts (NMI, silhouette, kBET, LISI, scIB-family metrics). Rejected: it would put beam in the ontology business it does not want to be in and would split the namespace from STATO. The honest gap with a proposed-upstream note is the correct response.
- Generate the OWL with ROBOT instead of rdflib. Rejected: ROBOT is a heavy dependency for the small artefact this release produces; rdflib is already in the Python toolchain and the OWL is plain enough that the extra ROBOT tooling does not earn its weight. A later release may bring ROBOT in if axiom generation grows.
- Encode the IRIs as short CURIEs (e.g. `STATO:0000593`) instead of full IRIs. Rejected: CURIEs need a prefix table that lives elsewhere and that downstream consumers may not share; full IRIs are self-resolving and survive serialization round-trips through any RDF tool.
- Save the OWL as RDF/XML. Rejected: Turtle is easier to inspect by hand, the asserted triples are short enough that line-by-line review is the natural sanity check, and rdflib parses either format with the same fidelity.

## References

- [docs/explanations/ontology-mappings.md](../explanations/ontology-mappings.md) for the user-facing essay, the per-card coverage table, and how to populate `mappings` on a new card.
- [docs/beam.owl.ttl](../beam.owl.ttl) for the release artefact.
- STATO Statistics Ontology: http://purl.obolibrary.org/obo/stato.owl ; landing page https://stato-ontology.org/ .
- Units of Measurement Ontology (UO): https://github.com/bio-ontology-research-group/unit-ontology .
- Ontology for Biomedical Investigations (OBI): https://obi-ontology.org/ .
- HuggingFace evaluate metric cards: https://github.com/huggingface/evaluate/tree/main/metrics .
- EBI Ontology Lookup Service: https://www.ebi.ac.uk/ols4 .
