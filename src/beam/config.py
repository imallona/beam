"""Run a benchmark recommendation from a declarative beam.yaml file.

beam.yaml captures a whole run in one diff-able file: the input scores, the
metrics, the weighting and aggregation, the sensitivity settings, and the
output paths. It is the artifact a reviewer reruns. ``run_config`` parses it,
runs ``beam.rank``, and writes the requested outputs (the HTML report, the run
manifest, and the normalized scores).

A minimal file::

    inputs:
      scores: scores.csv
    weighting:
      method: entropy
    aggregation:
      method: topsis
    sensitivity:
      smaa: {n: 1000, seed: 42}
    missing: error
    outputs:
      report: report.html
      manifest: manifest.json
      scores_normalized: scores_norm.csv

The optional top-level ``missing`` key sets the missing-cell policy passed to
``beam.rank`` (``error`` by default, or ``available``, ``worst``, ``impute``).
The dataset_features and heterogeneity blocks are parsed but ignored here.
Per-metric version pins are recorded but not yet enforced; the registry
resolves the latest version.
"""

from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from .api import RunResult, rank
from .cards import Registry
from .io import Scores, load_scores
from .manifest import write_manifest
from .reporting import write_report


def load_config(path: str | Path) -> dict[str, Any]:
    """Parse a beam.yaml file and check the one required field is present."""
    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"{path} must contain a YAML mapping at the top level")
    inputs = config.get("inputs")
    if not isinstance(inputs, dict) or not inputs.get("scores"):
        raise ValueError(f"{path} must set inputs.scores to the path of a score CSV")
    return config


def run_config(path: str | Path, registry: Registry | None = None) -> RunResult:
    """Run the pipeline described by a beam.yaml file and write its outputs.

    Parameters
    ----------
    path
        Path to the beam.yaml file. Relative paths inside it are resolved
        against the file's own directory.
    registry
        Optional ``Registry``. Defaults to a fresh registry over the bundled
        metrics.

    Returns
    -------
    RunResult
    """
    path = Path(path)
    base = path.parent
    config = load_config(path)
    reg = registry if registry is not None else Registry()

    scores_path = base / config["inputs"]["scores"]
    scores = load_scores(scores_path, registry=reg)

    requested = _requested_metric_ids(config)
    if requested is not None:
        scores = _select_metrics(scores, requested)

    weighting = config.get("weighting", {}).get("method", "equal")
    method = config.get("aggregation", {}).get("method", "saw")

    sensitivity_block = config.get("sensitivity")
    sensitivity = sensitivity_block is not None
    smaa_block = (sensitivity_block or {}).get("smaa", {}) if sensitivity else {}
    smaa_samples = int(smaa_block.get("n", 1000))
    seed = int(smaa_block.get("seed", 42))
    missing = config.get("missing", "error")

    result = rank(
        scores,
        weights=weighting,
        method=method,
        sensitivity=sensitivity,
        missing=missing,
        smaa_samples=smaa_samples,
        seed=seed,
        registry=reg,
    )

    _write_outputs(result, config.get("outputs", {}), base, reg)
    return result


def _requested_metric_ids(config: dict[str, Any]) -> list[str] | None:
    metrics = config.get("metrics")
    if not metrics:
        return None
    return [m["id"] if isinstance(m, dict) else str(m) for m in metrics]


def _select_metrics(scores: Scores, ids: list[str]) -> Scores:
    available = list(scores.metric_ids)
    missing = [mid for mid in ids if mid not in available]
    if missing:
        raise ValueError(
            f"beam.yaml lists metrics not present in the scores file: {missing}; "
            f"available are {available}"
        )
    cols = [available.index(mid) for mid in ids]
    values = scores.values[:, :, cols] if scores.is_tensor else scores.values[:, cols]
    return replace(scores, values=values, metric_ids=tuple(ids))


def _write_outputs(
    result: RunResult,
    outputs: dict[str, Any],
    base: Path,
    registry: Registry,
) -> None:
    if not outputs:
        return
    if outputs.get("report"):
        write_report(result, base / outputs["report"], registry=registry)
    if outputs.get("manifest"):
        write_manifest(result.manifest, str(base / outputs["manifest"]))
    if outputs.get("scores_normalized"):
        _write_normalized_csv(result, base / outputs["scores_normalized"])


def _write_normalized_csv(result: RunResult, path: Path) -> None:
    normalized = result.result.normalized
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["tool", *result.metric_ids])
        for i, tool in enumerate(result.tool_names):
            writer.writerow([tool, *(f"{v:.6g}" for v in np.asarray(normalized[i]))])
