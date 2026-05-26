# 0004 - OpenProblems spatially variable genes, Bradley-Terry tree on correlation

- Status: Active
- Date: 2026-05-26
- Dataset: OpenProblems spatially variable genes task, 14 methods by 50 spatial datasets by one correlation metric (bundled openproblems_svg.csv) with the bundled dataset features (openproblems_svg_features.csv)
- Authors: Izaskun Mallona
- Commit: pending
- Manifest: tests/test_heterogeneity_bradley_terry.py (test_tree_splits_openproblems_svg)

## Observation

Fitting a Bradley-Terry tree on the per-dataset correlation comparisons, with categorical dataset features as candidate splitting variables, the parameter-stability test does find a split. This is the contrasting positive result to findings 0003, where the same machinery found no split on the 12 Duo datasets. The candidate features are parsed from each dataset id: technology (the spatial assay: visium, merfish, slideseqv2, stereoseq, dbitseq, seqfish, starmap, slidetags, post_xenium), organism (human, mouse, drosophila), and condition (cancer or noncancer). The global flat Bradley-Terry ranking over all 50 datasets is led by spark_x, then nnsvg, then gpcounts. The tree splits on technology and organism into 4 leaves at a minimal node size of 6 datasets:

- a leaf of merfish and stereoseq datasets (n=9), led by spark_x
- a leaf of dbitseq, merfish and starmap datasets (n=9), led by spark_x
- a leaf of seqfish, slideseqv2 and slidetags datasets (n=10), led by nnsvg
- a leaf of post_xenium and visium datasets (n=22, the largest), led by spanve

The pooled top method, spark_x, does not hold everywhere. On the 22 visium and xenium datasets the leading method is spanve, and on the seqfish, slideseqv2 and slidetags datasets it is nnsvg. The reversed_leaves diagnostic flags these two leaves. The best spatially variable gene method depends on the spatial assay technology, which is exactly the heterogeneity against one method fits all that the Bradley-Terry tree exists to surface, and which a single pooled ranking hides. This is the demonstration that Duo, at 12 datasets with no split, was too small to show.

## Method

Loaded the tensor with `beam.datasets.load_openproblems("spatially_variable_genes")`, took the correlation metric (higher is better, comparing a method's spatially variable gene ranking to a reference), and loaded the dataset features with `beam.datasets.load_openproblems_svg_features`. The 14 methods are real SVG methods; the random_ranking and true_ranking baselines were dropped at vendoring. `beam.heterogeneity.paired_comparisons` turned the matrix into per-dataset paired method comparisons (the higher correlation wins, NaN cells are missing comparisons), at a coverage of about 0.91, and `beam.heterogeneity.bradley_terry_tree` fit `psychotree::bttree(preference ~ technology + organism + condition)` through the one-shot R subprocess (ADR 0010). The datasets are the subjects whose features split the tree; the methods are the objects compared. The provenance of the bundled data is recorded in src/beam/data/README.md.

## Implications

This is the richer real input anticipated in findings 0003 and in PLAN Phase 5: 50 datasets carrying real feature variation, where the parameter-stability test can separate a feature-dependent regime from sampling noise. The split is read honestly. The tree is descriptive of these 50 datasets and the technologies available in them. The technology and organism features are confounded, since some assays appear in only one organism, so the split should be read as by assay and the organism that comes with it, not as two independent effects. With that caveat, the result is concrete: a benchmark consumer who reads only the pooled ranking would adopt spark_x everywhere, when on the largest group of datasets, the 22 visium and xenium ones, spanve leads, and on a third group nnsvg leads.

## Reproducibility

- Notebook or script: tests/test_heterogeneity_bradley_terry.py (test_tree_splits_openproblems_svg)
- Run manifest: the test pins the split on technology and organism, the 4 leaves and their sizes, the per-leaf leading method, the two reversed leaves, and spark_x as the leading global strength
- Commit: pending
- Software environment: R 4.3.3, psychotree, partykit, psychotools; Python 3.12, numpy, the beam-heterogeneity conda environment (envs/heterogeneity.yml)

## Related

- Contrasts with [findings 0003](0003-duo-2018-bradley-terry-tree.md) (Duo, no split) and [findings 0002](0002-duo-2018-variance-decomposition.md) (variance decomposition)
- Method explained in [the Bradley-Terry trees explanation](../explanations/heterogeneity-bradley-terry.md); decision in [ADR 0010](../adr/0010-bradley-terry-trees.md); data provenance in src/beam/data/README.md
- External references: OpenProblems consortium. Nature Biotechnology 2025. DOI 10.1038/s41587-025-02694-w
