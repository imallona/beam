"""Reduce the DeepCellSeek supplement to the bundled beam tables.

Source: the LLM cell type annotation benchmark of DeepCellSeek (Xiao, Hua, Wang,
Lu and Zhang, Briefings in Bioinformatics 2025, DOI 10.1093/bib/bbaf677). It scores 11 LLM
endpoints and three reference-based annotators (CellMarker2.0, SingleR, ScType)
on the same ontology-aware agreement metric as Hou and Ji (2024): per cell type,
1 for a full match to the manual annotation, 0.5 for a partial match, 0 for a
mismatch.

The per-cell-type scores are in Supplementary Table 4 of the article supplement
file ``supplementary_table_bbaf677.xlsx`` (sheet "Supplementary Table 4"). The
article is CC-BY-NC; numerical results in a published table are facts not subject
to copyright, so the derived per-(dataset, method) scores are vendored here with
attribution, the same basis used for the Tyler 2023 integration table. beam's
role is reanalysis under one consistent rule, not redistribution of the text.

The OUP supplement download link is signed and expires, so there is no stable
raw URL. Download ``supplementary_table_bbaf677.xlsx`` from the article's
supplementary data section, then run:

    python reduce_deepcellseek.py path/to/supplementary_table_bbaf677.xlsx

It writes two tables next to this script:

- deepcellseek2025_agreement.csv: long format source, tissue, dataset, type,
  cell_type, method, score. One row per cell type per method.
- deepcellseek2025_features.csv: one row per (source, tissue) dataset with
  species, source, tissue and n_cell_types.

Requires openpyxl (a one-off, not a beam runtime dependency).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import openpyxl

# Score column header in the supplement -> readable method name. The three
# reference-based annotators are named to match the GPTCelltype table exactly so
# the two benchmarks share method labels.
SCORE_COLUMN_METHOD = {
    "Claude-3.7 Score": "Claude-3.7",
    "Claude-4.1 Score": "Claude-4.1",
    "DeepSeek-R1 Score": "DeepSeek-R1",
    "Doubao-1.6 Score": "Doubao-1.6",
    "Gemini-2.0 Score": "Gemini-2.0",
    "Gemini-2.5 Score": "Gemini-2.5",
    "GPT-4o Score": "GPT-4o",
    "GPT-5 Score": "GPT-5",
    "Grok-3 Score": "Grok-3",
    "Grok-4 Score": "Grok-4",
    "Kimi-k2 Score": "Kimi-k2",
    "Cellmarker Score": "CellMarker2.0",
    "Sctype Score": "ScType",
    "singleR Score": "SingleR",
}


def dataset_id(source: str, tissue: str) -> str:
    if not tissue or tissue == "NA":
        return source.replace(" ", "_")
    return f"{source}_{tissue}".replace(" ", "_")


def reduce(xlsx_path: str) -> None:
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb["Supplementary Table 4"]
    rows = list(ws.iter_rows(min_row=5, values_only=True))
    header = list(rows[0])
    index = {name: i for i, name in enumerate(header)}
    col = {h: index[h] for h in SCORE_COLUMN_METHOD if h in index}

    here = Path(__file__).resolve().parent
    agreement_rows = []
    feature_rows: dict[str, dict[str, object]] = {}
    for row in rows[1:]:
        source = row[index["Dataset"]]
        if not source:
            continue
        tissue = row[index["Tissue"]] or ""
        species = row[index["Species"]] or ""
        cell_type = row[index["Expert Annotation"]] or ""
        type_label = row[index["Type"]] or ""
        did = dataset_id(str(source), str(tissue))
        for score_header, method in SCORE_COLUMN_METHOD.items():
            if score_header not in col:
                continue
            value = row[col[score_header]]
            if value in (None, ""):
                continue
            agreement_rows.append(
                {
                    "source": source,
                    "tissue": tissue,
                    "dataset": did,
                    "type": type_label,
                    "cell_type": cell_type,
                    "method": method,
                    "score": f"{float(value):g}",
                }
            )
        entry = feature_rows.setdefault(
            did,
            {
                "dataset": did,
                "source": source,
                "tissue": tissue,
                "species": str(species).lower(),
                "n_cell_types": 0,
            },
        )
        entry["n_cell_types"] = int(entry["n_cell_types"]) + 1

    with (here / "deepcellseek2025_agreement.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["source", "tissue", "dataset", "type", "cell_type", "method", "score"]
        )
        writer.writeheader()
        writer.writerows(agreement_rows)

    with (here / "deepcellseek2025_features.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["dataset", "source", "tissue", "species", "n_cell_types"]
        )
        writer.writeheader()
        writer.writerows(feature_rows.values())

    print(f"wrote {len(agreement_rows)} score rows over {len(feature_rows)} datasets")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python reduce_deepcellseek.py supplementary_table_bbaf677.xlsx")
    reduce(sys.argv[1])
