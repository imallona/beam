"""Reduce the Shen 2026 semi-supervised integration benchmark to a bundled table.

Source: the semi-supervised scRNA-seq integration benchmark of Shen, He and Guan
(PLOS Computational Biology 2026, DOI 10.1371/journal.pcbi.1014008). It scores ten
integration methods (five semi-supervised: scANVI, scGEN, STACAS, scDREAMER,
ItClust; five unsupervised: Seurat, scVI, Harmony, scanorama, scCRAFT) on six
datasets under a range of annotation scenarios, on the scIB metric family.

The per-(dataset, scenario, method, metric) scores are the raw scIB output in the
authors' repository (https://github.com/RainySheena/benchmark_semi) under
metrics_by_datasets/results/, one CSV per dataset. The six CSVs do not share a
column layout: most are type, metric, method, score; lung_atlas carries a UTF-8
BOM on the first header; lung_two_species swaps method and metric; macaque names
the scenario column file_path and the method column embedding_key. This script
normalizes the layouts and concatenates them into one long table.

The repository ships no license file. Numerical results in a published benchmark
are facts not subject to copyright, so the derived per-(dataset, scenario, method,
metric) scores are vendored here with attribution, the same basis used for the
Tyler 2023 and DeepCellSeek 2025 tables. beam's role is reanalysis under one
consistent rule, not redistribution of the article text or figures. Cite Shen,
He and Guan (2026).

Run with no arguments to fetch the six CSVs from the pinned commit and write the
bundled table next to this script:

    python reduce_shen.py

Pass a directory holding the six raw ``<dataset>_metrics.csv`` files to reduce a
local copy instead:

    python reduce_shen.py path/to/metrics_by_datasets/results
"""

from __future__ import annotations

import csv
import sys
import urllib.request
from pathlib import Path

PINNED_COMMIT = "f311f17dcc8f2f6fc5eb6a5bc9e16ec2007e4883"
RAW_BASE = (
    "https://raw.githubusercontent.com/RainySheena/benchmark_semi/"
    f"{PINNED_COMMIT}/metrics_by_datasets/results"
)
DATASETS = (
    "human_pancreas",
    "human_immune",
    "lung_atlas",
    "lung_two_species",
    "macaque",
    "bct",
)

# Source header name (BOM-stripped) -> normalized field name. macaque uses
# file_path for the annotation scenario and embedding_key for the method.
HEADER_ALIAS = {"file_path": "scenario", "type": "scenario", "embedding_key": "method"}


def _normalize_header(name: str) -> str:
    name = name.lstrip("﻿").strip()
    return HEADER_ALIAS.get(name, name)


def _read_dataset(dataset: str, source_dir: Path | None) -> list[dict[str, str]]:
    if source_dir is not None:
        text = (source_dir / f"{dataset}_metrics.csv").read_text(encoding="utf-8")
    else:
        with urllib.request.urlopen(f"{RAW_BASE}/{dataset}_metrics.csv") as fh:
            text = fh.read().decode("utf-8")
    reader = csv.reader(text.splitlines())
    header = [_normalize_header(h) for h in next(reader)]
    index = {h: i for i, h in enumerate(header)}
    rows = []
    for row in reader:
        if not row or not row[index["score"]]:
            continue
        rows.append(
            {
                "dataset": dataset,
                "scenario": row[index["scenario"]].strip(),
                "method": row[index["method"]].strip(),
                "metric": row[index["metric"]].strip(),
                "score": f"{float(row[index['score']]):.6g}",
            }
        )
    return rows


def reduce(source_dir: Path | None) -> None:
    records: list[dict[str, str]] = []
    for dataset in DATASETS:
        records.extend(_read_dataset(dataset, source_dir))
    records.sort(key=lambda r: (r["dataset"], r["scenario"], r["method"], r["metric"]))

    here = Path(__file__).resolve().parent
    with (here / "shen2026_metrics.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["dataset", "scenario", "method", "metric", "score"])
        writer.writeheader()
        writer.writerows(records)

    datasets = sorted({r["dataset"] for r in records})
    methods = sorted({r["method"] for r in records})
    metrics = sorted({r["metric"] for r in records})
    print(
        f"wrote {len(records)} score rows over {len(datasets)} datasets, "
        f"{len(methods)} methods, {len(metrics)} metrics"
    )


if __name__ == "__main__":
    if len(sys.argv) > 2:
        raise SystemExit("usage: python reduce_shen.py [metrics_by_datasets/results]")
    reduce(Path(sys.argv[1]) if len(sys.argv) == 2 else None)
