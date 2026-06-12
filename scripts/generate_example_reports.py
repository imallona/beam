"""Generate one self-contained HTML report per bundled dataset.

Each report is what ``beam.report`` emits for a real run, so a reader can see
the generated artefact for every dataset beam ships, not only the worked
vignettes. The docs site links these; the script also runs standalone:

    python scripts/generate_example_reports.py --out docs/reports

It writes ``<name>.html`` per dataset. The docs home and each vignette link to
these directly, so there is no separate index page. A dataset that fails to
build is skipped with a message rather than failing the whole run, so one
missing optional dependency does not block the rest.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

import beam
from beam.datasets import load_duo2018, load_gptcelltype, load_m4, load_openproblems


def _duo() -> tuple[beam.Scores, dict]:
    duo = load_duo2018()
    metric_ids = ("ari", "runtime", "shannon_entropy_diff")
    tensor = duo.tensor(metric_ids)
    complete = duo.complete_methods(metric_ids)
    scores = beam.Scores(
        values=tensor[complete],
        tool_names=tuple(np.array(duo.method_names)[complete].tolist()),
        metric_ids=metric_ids,
        dataset_names=duo.dataset_names,
        layout="long",
    )
    return scores, {"weights": "equal", "method": "saw", "ground_truth_tool": "Seurat"}


def _m4() -> tuple[beam.Scores, dict]:
    m4 = load_m4()
    scores = beam.Scores(
        values=m4.tensor(),
        tool_names=m4.method_names,
        metric_ids=m4.metric_ids,
        dataset_names=m4.frequency_names,
        layout="long",
    )
    return scores, {"weights": "equal", "method": "saw", "seed": 0}


def _openproblems() -> tuple[beam.Scores, dict]:
    op = load_openproblems("batch_integration")
    metrics = tuple(m for m in op.metric_ids if m != "hvg_overlap")
    tensor = op.tensor(metrics)
    keep = (~np.isnan(tensor).all(axis=1)).all(axis=1)
    scores = beam.Scores(
        values=tensor[keep],
        tool_names=tuple(m for m, k in zip(op.method_names, keep, strict=True) if k),
        metric_ids=metrics,
        dataset_names=op.dataset_names,
        layout="long",
    )
    return scores, {"weights": "equal", "method": "topsis"}


def _gptcelltype() -> tuple[beam.Scores, dict]:
    g = load_gptcelltype()
    head = ["GPT-4", "GPT-3.5", "CellMarker2.0", "SingleR", "ScType"]
    idx = [g.method_names.index(m) for m in head]
    sub = g.scores[idx]
    complete = ~np.isnan(sub[:, :, 0]).any(axis=0)
    block = sub[:, complete, :]
    datasets = tuple(d for d, keep in zip(g.dataset_names, complete, strict=True) if keep)
    scores = beam.Scores(
        values=block,
        tool_names=tuple(head),
        metric_ids=tuple(g.metric_ids),
        dataset_names=datasets,
        layout="long",
    )
    return scores, {"weights": "equal", "method": "saw", "ground_truth_tool": "GPT-4"}


DATASETS = {
    "duo2018": ("Duo et al. 2018 single-cell clustering", _duo),
    "m4": ("M4 forecasting competition", _m4),
    "openproblems_batch_integration": ("OpenProblems batch integration", _openproblems),
    "gptcelltype": ("Hou and Ji 2024 LLM cell type annotation", _gptcelltype),
}


def generate(out_dir: Path) -> list[tuple[str, str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[tuple[str, str]] = []
    for name, (title, build) in DATASETS.items():
        try:
            scores, kwargs = build()
            ground_truth = kwargs.pop("ground_truth_tool", None)
            run = beam.rank(scores, **kwargs)
            beam.report(
                run, str(out_dir / f"{name}.html"), title=title, ground_truth_tool=ground_truth
            )
            written.append((name, title))
            print(f"wrote {name}.html ({title})")
        except Exception as exc:
            print(f"skipped {name}: {exc}")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="generate one beam report per bundled dataset")
    parser.add_argument("--out", default="docs/reports", help="output directory")
    args = parser.parse_args()
    generate(Path(args.out))


if __name__ == "__main__":
    main()
