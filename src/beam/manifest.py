"""The run manifest: the reproducibility envelope written next to a report.

A manifest records everything needed to reproduce a beam recommendation: the
beam version, the input and its hash, the metric cards with their versions and
content hashes, the weighting and aggregation, the per-metric normalization,
the sensitivity settings including the SMAA seed, and a software fingerprint
that includes pymcdm, since the aggregation math is delegated to it and the
rankings depend on its version.

Two runs over the same inputs and settings produce the same manifest apart
from the wall-clock timestamp and the host fingerprint, which live under the
``created_utc`` and ``host`` keys so a determinism check can drop them. Use
``volatile_keys`` for that.
"""

from __future__ import annotations

import hashlib
import json
import platform
import socket
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib import metadata
from typing import Any

import numpy as np

from .cards import Registry
from .io import Scores

# Keys that legitimately differ between two otherwise identical runs.
volatile_keys = ("created_utc", "host")

_SOFTWARE_PACKAGES = ("beam", "numpy", "scipy", "pymcdm", "pyyaml", "jsonschema")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _input_fingerprint(scores: Scores) -> dict[str, Any]:
    if scores.source_path is not None:
        with open(scores.source_path, "rb") as handle:
            digest = _sha256_bytes(handle.read())
        return {"path": scores.source_path, "sha256": digest}
    # Constructed from arrays: hash the values so determinism still holds.
    contiguous = np.ascontiguousarray(scores.values)
    return {"path": None, "sha256": _sha256_bytes(contiguous.tobytes())}


def _card_fingerprint(metric_id: str, registry: Registry) -> dict[str, Any]:
    card = registry.get(metric_id)
    canonical = json.dumps(card.raw, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"id": card.id, "version": card.version, "sha256": _sha256_bytes(canonical)}


def _software_fingerprint() -> dict[str, str]:
    out: dict[str, str] = {"python": platform.python_version()}
    for name in _SOFTWARE_PACKAGES:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = "not installed"
    return out


def build_manifest(
    scores: Scores,
    metric_ids: Sequence[str],
    weighting: str,
    method: str,
    normalization: Sequence[str],
    sensitivity: bool,
    smaa_samples: int | None,
    smaa_seed: int | None,
    registry: Registry,
) -> dict[str, Any]:
    """Assemble the manifest dictionary for one beam run.

    Parameters
    ----------
    scores
        The input container. Its ``source_path`` and values feed the input
        fingerprint.
    metric_ids
        Ordered metric ids used in the run.
    weighting
        The weighting scheme name, or ``"user-supplied"``.
    method
        The aggregation method name.
    normalization
        Per-metric normalization strategy, aligned with ``metric_ids``.
    sensitivity
        Whether the default sensitivity primitives were run.
    smaa_samples, smaa_seed
        SMAA sample count and seed, recorded when sensitivity ran.
    registry
        Registry used to resolve card versions and content hashes.

    Returns
    -------
    dict
        A JSON-serializable manifest. ``created_utc`` and ``host`` are the
        only keys that vary between identical runs; see ``volatile_keys``.
    """
    metric_ids = list(metric_ids)
    manifest: dict[str, Any] = {
        "beam_version": _software_fingerprint()["beam"],
        "created_utc": datetime.now(UTC).isoformat(),
        "host": {"hostname": socket.gethostname(), "platform": platform.platform()},
        "input": _input_fingerprint(scores),
        "layout": scores.layout,
        "tools": list(scores.tool_names),
        "metrics": [_card_fingerprint(mid, registry) for mid in metric_ids],
        "weighting": {"method": weighting},
        "aggregation": {"method": method},
        "normalization": [
            {"metric": mid, "strategy": strat}
            for mid, strat in zip(metric_ids, normalization, strict=True)
        ],
        "sensitivity": {
            "enabled": sensitivity,
            "smaa": {"n_samples": smaa_samples, "seed": smaa_seed} if sensitivity else None,
            "leave_one_metric_out": sensitivity,
            "smallest_weight_perturbation": sensitivity,
        },
        "software": _software_fingerprint(),
    }
    return manifest


def write_manifest(manifest: dict[str, Any], path: str) -> None:
    """Write a manifest to ``path`` as indented JSON with a trailing newline."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")


def reproducible_view(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the manifest without the keys that vary per run.

    Drops ``created_utc`` and ``host`` so two manifests from identical inputs
    can be compared for equality.
    """
    return {k: v for k, v in manifest.items() if k not in volatile_keys}
