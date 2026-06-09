# AnnDictionary scores

## Citation

Crowley G, et al. Benchmarking cell type and gene set annotation by large
language models with AnnDictionary. Nature Communications 2025, 16:9511.
DOI 10.1038/s41467-025-64511-x. https://www.nature.com/articles/s41467-025-64511-x

- First author George Crowley; senior author Stephen R. Quake (large consortium
  author list, abbreviated here as "et al.").
- Code: https://github.com/ggit12/anndictionary
- Supplementary source data:
  https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-025-64511-x/MediaObjects/41467_2025_64511_MOESM4_ESM.zip

## License and copyright

The article is open access under CC-BY (Nature Communications), which is the
basis for reusing these numbers with attribution. There is no clearer statement
than that on the data itself: the supplementary zip (`MOESM4_ESM.zip`) ships no
explicit license file and the values are inside Python pickles under
`source_data/`. The authors remain the copyright holders. Confirm the CC-BY
coverage before redistributing in a released artifact. This file is kept in this
subfolder so it is not packaged into the beam wheel (the wheel glob is
`src/beam/data/*.csv`, which does not match subfolders).

## What is here

`anndictionary_celltype_agreement.csv`: per-model annotation performance from
`source_data/table_1/run_{1..5}_performance_table.pkl`, averaged over the five
runs. Columns: `model`, `overall_binary_celltypes_mean` (ontology-aware binary
agreement against the manual `cell_ontology_class`, share of cell types) and
`perfect_match_celltypes_mean` (perfect categorical match share). Values are
fractions in [0, 1].

This benchmark is LLM-only: 13 LLMs plus a `Plurality Vote` ensemble, with no
classical reference annotator (no SingleR, ScType or CellMarker2.0). The ground
truth is the manual `cell_ontology_class`. It contributes an LLM-only arm to a
cross-benchmark comparison and links to the other benchmarks through the shared
LLM endpoints (GPT-4, GPT-4o).
