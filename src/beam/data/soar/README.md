# SOAR (Single-Cell Omics Arena) scores

## Citation

Liu J, Xu S, Zhang L, Zhang J. Single-Cell Omics Arena: A Benchmark Study for
Large Language Models on Cell Type Annotation Using Single-Cell Data.
arXiv:2412.02915 (2024). https://arxiv.org/abs/2412.02915

- Authors: Junhao Liu, Siwei Xu, Lei Zhang, Jing Zhang.
- Code: https://github.com/aicb-ZhangLabs/SOAR
- Scores read from commit `e5d2b3e2619cb56fece5fba78fae989a67fd0c13` (file `readme.md`).

## License and copyright

There is no clear license. The repository has no LICENSE file, the README states
no license, and the arXiv preprint carries no Creative Commons or open license by
default. The authors (Liu, Xu, Zhang, Zhang) remain the copyright holders. The
numbers here are transcribed from the published README only as factual results
for reanalysis, with attribution, and should not be redistributed in a released
artifact without the authors' permission. This file is kept in this subfolder so
it is not packaged into the beam wheel (the wheel glob is `src/beam/data/*.csv`,
which does not match subfolders).

## What is here

`soar_readme_scores.csv`: the per-model benchmark tables from the README at the
pinned commit. Columns: `table_name`, `model`, and the NLP overlap metrics `R-1`,
`R-2`, `R-L` (ROUGE), `METEOR`, `BLEU-1`, `BLEU-2`, `BLEU`. Four tables:
SOAR-RNA Zero-shot, SOAR-RNA Zero-shot-CoT, SOAR-MultiOmics RNA-seq,
SOAR-MultiOmics ATAC-seq. Values are percentages, as printed.

The metric family is NLP text overlap, not the ontology-aware agreement of
GPTCelltype and DeepCellSeek, so SOAR enters a cross-benchmark comparison on the
within-benchmark rank scale, not on a shared metric. The reference-based methods
CellMarker2.0, SingleR, ScType and Cell2Sentence have scores only in the
SOAR-RNA Zero-shot table; the README reports aggregate scores per table, not per
dataset.
