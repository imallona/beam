"""Reduce the scIB deep-learning method scores to a bundled table.

Source: the scIB benchmark of Luecken et al. (Nature Methods 2022, DOI
10.1038/s41592-021-01336-8), reproduction repository theislab/scib-reproducibility,
file data/metrics.csv. The bundled scib2022_metrics.csv keeps the five classical
methods from this same file; this script extracts the deep-learning methods it
also scores on the identical datasets and metrics, so the two families can be
contrasted on the same data.

The metrics.csv index column encodes /dataset/metrics/{scaled,unscaled}/
{feature_space}/{variant}. This script keeps the unscaled rows for the five real
datasets (immune_cell_hum, immune_cell_hum_mou, lung_atlas, mouse_brain,
pancreas), the four metric columns shared with the classical block
(ARI_cluster/label, ASW_label, kBET, iLISI mapped to ARI, ASW, kBET, LISI), and
one representative integration variant per deep-learning method. Both feature
spaces (hvg and full_feature) are emitted as separate rows; the loader averages
them, as it does for the classical block. A cell the source leaves blank is
dropped, never imputed.

Code in the source repository is MIT and the article is CC-BY 4.0; cite Luecken
et al. 2022. beam's role is reanalysis under one consistent rule.

Run with no arguments to fetch metrics.csv from the pinned commit and write the
bundled table next to this script:

    python reduce_scib_dl.py

Pass a local copy of metrics.csv to reduce it instead:

    python reduce_scib_dl.py path/to/metrics.csv
"""

from __future__ import annotations

import csv
import sys
import urllib.request
from pathlib import Path

PINNED_COMMIT = "5f9c08e213c714db70f96144acd4179f9481c3d2"
RAW_URL = (
    "https://raw.githubusercontent.com/theislab/scib-reproducibility/"
    f"{PINNED_COMMIT}/data/metrics.csv"
)

REAL_DATASETS = frozenset(
    {"immune_cell_hum", "immune_cell_hum_mou", "lung_atlas", "mouse_brain", "pancreas"}
)
# Source metric column -> bundled metric id, the four shared with the classical
# block. All four are higher-is-better in scIB's unscaled output.
METRIC_COLUMN = {"ARI_cluster/label": "ARI", "ASW_label": "ASW", "kBET": "kBET", "iLISI": "LISI"}
# Source variant -> deep-learning method name. One representative variant each,
# the embedding output where the method offers one, matching how the classical
# block takes harmony_embed, scanorama_embed and so on.
DL_VARIANT = {
    "scvi_embed": "scVI",
    "scanvi_embed": "scANVI",
    "scgen_full": "scGen",
    "desc_embed": "DESC",
    "saucie_embed": "SAUCIE",
    "trvae_embed": "trVAE",
}


def _read_metrics(source: Path | None) -> list[dict[str, str]]:
    if source is not None:
        text = source.read_text(encoding="utf-8")
    else:
        with urllib.request.urlopen(RAW_URL) as fh:
            text = fh.read().decode("utf-8")
    reader = csv.DictReader(text.splitlines())
    index_field = reader.fieldnames[0]

    records: list[dict[str, str]] = []
    for row in reader:
        parts = row[index_field].strip("/").split("/")
        if len(parts) < 5 or parts[1] != "metrics" or parts[2] != "unscaled":
            continue
        dataset, variant = parts[0], parts[4]
        if dataset not in REAL_DATASETS or variant not in DL_VARIANT:
            continue
        method = DL_VARIANT[variant]
        for column, metric in METRIC_COLUMN.items():
            value = row.get(column, "")
            if value == "" or value is None:
                continue
            records.append(
                {
                    "dataset": dataset,
                    "method": method,
                    "metric": metric,
                    "score": f"{float(value):.6g}",
                }
            )
    return records


def reduce(source: Path | None) -> None:
    records = _read_metrics(source)
    records.sort(key=lambda r: (r["dataset"], r["method"], r["metric"]))

    here = Path(__file__).resolve().parent
    with (here / "scib2022_dl_metrics.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["dataset", "method", "metric", "score"])
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
        raise SystemExit("usage: python reduce_scib_dl.py [metrics.csv]")
    reduce(Path(sys.argv[1]) if len(sys.argv) == 2 else None)
