# STATO term proposals for gapped metrics

The per-card coverage table in [ontology mappings](ontology-mappings.md) lists the metrics that carry no STATO term today. This document drafts the upstream proposals for the gaps beam cares about for the long run. They can be filed against the STATO issue tracker at https://github.com/ISA-tools/stato/issues rather than filled by a beam-private IRI. Each proposal gives a label, a definition, a likely parent class, and the beam card it comes from. The proposals ask STATO to assign the identifier; beam does not mint one.

These cover the Group 1 gaps only. The operational measurands (runtime, peak_memory) and the [transportation metrics](../../examples/transportation/transportation.qmd) (cost, speed, co2) are anchored by UO where a unit exists and are out of STATO scope, so they are not proposed here.

## How to file one

Open an issue on the STATO tracker with the proposed label, the definition, and the parent class named below. Attach the primary reference. When STATO assigns an IRI, write it into the matching card under `mappings.stato`, regenerate the OWL artefact with `python -m beam.owl.generate`, and update the coverage table in [ontology mappings](ontology-mappings.md).

## Proposals

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

## Low-priority gaps

These scIB-specific scores are unlikely to earn a dedicated STATO term, but the gap is recorded for completeness: nclust_deviation, hvg_overlap, graph_connectivity, cell_cycle_conservation. Each stays anchored to its data-producing assay through OBI_0002631 on the card. A proposal would only make sense if a wider community adopts these scores beyond scIB.
