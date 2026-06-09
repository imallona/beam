"""Reduce the GPTCelltype paper annotation results to the bundled beam tables.

Source: the cell type annotation benchmark of Hou and Ji (Nature Methods 2024,
DOI 10.1038/s41592-024-02235-4), reproduction repository Winnie09/GPTCelltype_Paper.
The compiled per-cell-type evaluation table is anno/compiled/all.csv, pulled from
one pinned commit so the reduction is reproducible:

    repo:   github.com/Winnie09/GPTCelltype_Paper
    commit: 5944a41511aacd368b45448e256d9625849704df
    file:   anno/compiled/all.csv

Run with no arguments to fetch that file from the pinned commit, or pass a local
path to all.csv as the first argument:

    python reduce_gptcelltype.py [path/to/all.csv]

It writes two tables next to this script:

- gptcelltype2024_agreement.csv: long format source, tissue, dataset, cell_type,
  manual_broadtype, method, agreement, broadtype. One row per cell type per
  method that was run, with the ontology-aware agreement score (1 full match,
  0.5 partial match, 0 mismatch) the paper assigns by comparing each prediction
  to the manual annotation. manual_broadtype is the broad lineage of the manual
  annotation and broadtype is the method's predicted broad lineage (empty when
  the method gave none), kept so a consensus check can ask whether the methods
  agree on a lineage that differs from the manual one. Rows where a method was
  not run on a cell type are dropped, so a method absent from a whole dataset
  surfaces as missing coverage downstream.
- gptcelltype2024_features.csv: one row per (source, tissue) dataset with the
  candidate Bradley-Terry splitting variables source, tissue, species and
  sample_type, plus n_cell_types.

The six source method columns map to readable method names:

    gpt4aug3       -> GPT-4
    gpt4mar23      -> GPT-4-mar2023
    gpt3.5aug3     -> GPT-3.5
    CellMarker2.0  -> CellMarker2.0
    SingleR        -> SingleR
    ScType         -> ScType
"""

from __future__ import annotations

import csv
import sys
import urllib.request
from pathlib import Path

PINNED_COMMIT = "5944a41511aacd368b45448e256d9625849704df"
SOURCE_URL = (
    "https://raw.githubusercontent.com/Winnie09/GPTCelltype_Paper/"
    f"{PINNED_COMMIT}/anno/compiled/all.csv"
)

METHOD_NAME = {
    "gpt4aug3": "GPT-4",
    "gpt4mar23": "GPT-4-mar2023",
    "gpt3.5aug3": "GPT-3.5",
    "CellMarker2.0": "CellMarker2.0",
    "SingleR": "SingleR",
    "ScType": "ScType",
}

# Mouse Cell Atlas is the only mouse source; the rest are human.
MOUSE_SOURCES = {"MCA"}
CANCER_SOURCES = {"BCL", "coloncancer", "lungcancer"}


def dataset_id(source: str, tissue: str) -> str:
    """Stable dataset id from the source and tissue columns.

    Tissue is ``NA`` for the whole-atlas sources HCL and MCA, where the source
    alone names the dataset; otherwise the id is source and tissue joined, with
    spaces collapsed to underscores so it is safe in a file or a plot label.
    """
    if tissue in ("", "NA"):
        return source
    return f"{source}_{tissue}".replace(" ", "_")


def reduce(all_csv_path: str | None) -> None:
    if all_csv_path is None:
        with urllib.request.urlopen(SOURCE_URL) as response:
            text = response.read().decode("utf-8")
    else:
        text = Path(all_csv_path).read_text(encoding="utf-8")
    rows = list(csv.DictReader(text.splitlines()))

    here = Path(__file__).resolve().parent
    agreement_rows = []
    for row in rows:
        source = row["dataset"]
        tissue = row["tissue"]
        did = dataset_id(source, tissue)
        cell_type = row["manual_annotation"]
        manual_broadtype = row["manual_broadtype"]
        for column, method in METHOD_NAME.items():
            value = row[f"{column}_agreement"]
            if value in ("", "NA"):
                continue
            broadtype = row[f"{column}_broadtype"]
            agreement_rows.append(
                {
                    "source": source,
                    "tissue": tissue,
                    "dataset": did,
                    "cell_type": cell_type,
                    "manual_broadtype": manual_broadtype,
                    "method": method,
                    "agreement": f"{float(value):g}",
                    "broadtype": "" if broadtype in ("", "NA") else broadtype,
                }
            )

    with (here / "gptcelltype2024_agreement.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "source",
                "tissue",
                "dataset",
                "cell_type",
                "manual_broadtype",
                "method",
                "agreement",
                "broadtype",
            ],
        )
        writer.writeheader()
        writer.writerows(agreement_rows)

    # One feature row per (source, tissue) dataset, in first-seen order.
    feature_rows: dict[str, dict[str, str]] = {}
    for row in rows:
        source = row["dataset"]
        tissue = row["tissue"]
        did = dataset_id(source, tissue)
        entry = feature_rows.setdefault(
            did,
            {
                "dataset": did,
                "source": source,
                "tissue": "" if tissue == "NA" else tissue,
                "species": "mouse" if source in MOUSE_SOURCES else "human",
                "sample_type": "cancer" if source in CANCER_SOURCES else "normal",
                "n_cell_types": 0,
            },
        )
        entry["n_cell_types"] += 1

    with (here / "gptcelltype2024_features.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["dataset", "source", "tissue", "species", "sample_type", "n_cell_types"],
        )
        writer.writeheader()
        writer.writerows(feature_rows.values())

    print(f"wrote {len(agreement_rows)} agreement rows over {len(feature_rows)} datasets")


if __name__ == "__main__":
    reduce(sys.argv[1] if len(sys.argv) > 1 else None)
