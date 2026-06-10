"""Hide method names during analysis, then restore them.

If a benchmarker can see which method is which while choosing the weighting, the
aggregation and the metric set, those choices can shift toward a preferred
method, with or without intent. Blind analysis avoids this: fix the pipeline on
data whose method labels are hidden, then reveal the labels. The practice comes
from particle physics and clinical trials (MacCoun and Perlmutter 2015; Klein and
Roodman 2005).

``blind`` replaces the tool names in a ``Scores`` with opaque labels and shuffles
the rows under a seed, returning the relabeled scores and a ``Seal`` that records
the mapping back to the true names. The analyst runs the full beam pipeline on
the blinded scores, fixes the configuration, then calls ``unblind`` with the seal
to restore the true names.

This is a record, not a guarantee. Software cannot stop a person from reading the
source file. The ``Seal`` carries a fingerprint (a hash of the mapping and the
seed) that beam writes into the run manifest, so a reviewer can confirm the
analysis ran on scores blinded under that seal. The seal file, kept separately,
records that the configuration was fixed before the labels were revealed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, replace

import numpy as np

from .io import Scores

_DEFAULT_PREFIX = "method"


@dataclass(frozen=True)
class Seal:
    """The secret that maps blinded labels back to true tool names.

    Attributes
    ----------
    mapping
        Blinded label to true tool name, one entry per tool.
    seed
        The seed that produced the row permutation, recorded so the blinding can
        be reproduced.
    """

    mapping: dict[str, str]
    seed: int

    @property
    def fingerprint(self) -> str:
        """A sha256 over the seed and the sorted mapping.

        Stable for a given blinding and safe to publish: it identifies the
        blinding without revealing the mapping in a readable form. beam records
        it in the run manifest.
        """
        canonical = json.dumps(
            {"seed": self.seed, "mapping": dict(sorted(self.mapping.items()))},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def true_name(self, blinded_label: str) -> str:
        """Return the true tool name for one blinded label."""
        return self.mapping[blinded_label]

    def translate(self, labels: Sequence[str]) -> list[str]:
        """Return the true tool names for a sequence of blinded labels."""
        return [self.mapping[label] for label in labels]

    def to_dict(self) -> dict:
        """Return a JSON-serializable view of the seal."""
        return {"seed": self.seed, "mapping": dict(self.mapping)}

    @classmethod
    def from_dict(cls, data: dict) -> Seal:
        """Build a seal from the dictionary produced by ``to_dict``."""
        return cls(mapping=dict(data["mapping"]), seed=int(data["seed"]))


def blind(
    scores: Scores, seed: int = 0, label_prefix: str = _DEFAULT_PREFIX
) -> tuple[Scores, Seal]:
    """Relabel and shuffle the tools of a score table, returning a seal.

    The tool axis is permuted under ``seed`` and renamed to opaque labels such as
    ``method_1``, ``method_2``, so neither the names nor the row order carry the
    methods' identity. The metric and dataset axes are left unchanged, since the
    analyst needs them to set polarity, weights and the cross-dataset rule. The
    returned scores carry the seal fingerprint so a run on them records the
    blinding in its manifest.

    Parameters
    ----------
    scores
        The score table or tensor to blind.
    seed
        Seed for the row permutation. The same seed reproduces the same blinding.
    label_prefix
        Prefix for the opaque labels. Default ``"method"``.

    Returns
    -------
    tuple of (Scores, Seal)
        The blinded scores and the seal that unblinds them.

    Examples
    --------
    >>> import numpy as np
    >>> from beam import Scores, blind, unblind
    >>> s = Scores(
    ...     values=np.array([[0.9, 0.1], [0.5, 0.5]]),
    ...     tool_names=("seurat", "sc3"),
    ...     metric_ids=("ari", "runtime"),
    ...     dataset_names=None,
    ...     layout="wide",
    ... )
    >>> blinded, seal = blind(s, seed=1)
    >>> set(blinded.tool_names) == {"method_1", "method_2"}
    True
    >>> set(seal.mapping.values()) == {"seurat", "sc3"}
    True
    >>> tuple(unblind(blinded, seal).tool_names) == tuple(seal.translate(blinded.tool_names))
    True
    """
    n = scores.n_tools
    perm = np.random.default_rng(seed).permutation(n)
    width = len(str(n))
    blinded_labels = tuple(f"{label_prefix}_{i + 1:0{width}d}" for i in range(n))
    mapping = {blinded_labels[r]: scores.tool_names[perm[r]] for r in range(n)}
    seal = Seal(mapping=mapping, seed=int(seed))
    blinded = replace(
        scores,
        values=scores.values[perm],
        tool_names=blinded_labels,
        source_path=None,
        blinding_sha256=seal.fingerprint,
    )
    return blinded, seal


def unblind(obj, seal: Seal):
    """Restore the true tool names on a blinded ``Scores`` or ``RunResult``.

    The tool rows keep their blinded order; only the names are translated back
    through the seal. The blinding fingerprint is cleared, since the object is no
    longer blinded.

    Parameters
    ----------
    obj
        A ``Scores`` blinded by ``blind``, or a ``RunResult`` from ranking such a
        ``Scores``.
    seal
        The seal returned alongside the blinded scores.

    Returns
    -------
    The same type as ``obj``, with true tool names.

    Raises
    ------
    TypeError
        If ``obj`` is neither a ``Scores`` nor a ``RunResult``.
    """
    from .api import RunResult

    if isinstance(obj, Scores):
        return _unblind_scores(obj, seal)
    if isinstance(obj, RunResult):
        return replace(obj, scores=_unblind_scores(obj.scores, seal))
    raise TypeError(f"unblind handles Scores and RunResult, not {type(obj).__name__}")


def _unblind_scores(scores: Scores, seal: Seal) -> Scores:
    return replace(
        scores,
        tool_names=tuple(seal.translate(scores.tool_names)),
        blinding_sha256=None,
    )


def write_seal(seal: Seal, path: str) -> None:
    """Write a seal to ``path`` as indented JSON with a trailing newline."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(seal.to_dict(), handle, indent=2, sort_keys=True)
        handle.write("\n")


def read_seal(path: str) -> Seal:
    """Read a seal written by ``write_seal``."""
    with open(path, encoding="utf-8") as handle:
        return Seal.from_dict(json.load(handle))
