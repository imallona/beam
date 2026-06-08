"""Bradley-Terry trees on per-dataset method comparisons.

A global MCDA ranking pools every dataset into one recommendation. The
Bradley-Terry tree (Strobl, Wickelmaier and Zeileis) asks the sharper
question behind the "against one method fits all" critique: which dataset
properties reverse the ranking. For each dataset the methods are compared
pairwise on one metric (a win, a loss, or a tie per method pair), and a
Bradley-Terry model turns those outcomes into a latent strength per method.
Model-based recursive partitioning then splits the datasets by their
features so that each leaf has its own Bradley-Terry ranking, with a
parameter-stability test deciding where a split is warranted. The result
reads as "on datasets with feature X above threshold Z prefer method A,
otherwise prefer method B", which a single pooled number cannot give.

The subjects of the tree are the datasets (their features are the splitting
variables); the objects being compared are the methods. The model is fit by
R's psychotree in a one-shot subprocess, the same boundary as the
mixed-effects wrapper. Use
``bttree_available`` to check the R toolchain before calling
``bradley_terry_tree``.

Honest small-sample limit: model-based recursive partitioning needs enough
datasets to support a split. With a dozen datasets (the Duo 2018 case) the
test often finds no stable split and the report degrades to a single flat
Bradley-Terry ranking, which it says plainly. The tree earns its keep on a
benchmark with many datasets carrying real feature variation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ._rsubprocess import (
    RExecutionError,
    RNotAvailableError,
    packages_available,
    run_rscript,
)

_R_PACKAGE = "beam.heterogeneity"
_R_SCRIPT = "bradley_terry.R"
_R_PACKAGES = ("psychotree", "jsonlite")
_FIT_TIMEOUT_SECONDS = 300

_POLARITIES = ("higher_is_better", "lower_is_better")

__all__ = [
    "BTNode",
    "BradleyTerryTreeReport",
    "RExecutionError",
    "RNotAvailableError",
    "bradley_terry_tree",
    "bttree_available",
    "paired_comparisons",
]


def bttree_available() -> bool:
    """Return True when Rscript and the psychotree and jsonlite packages are present.

    Tests and vignettes use this to skip the analysis cleanly on a machine
    without the R toolchain. psychotree pulls in partykit and psychotools.
    """
    return packages_available(_R_PACKAGES)


def paired_comparisons(
    matrix: np.ndarray, polarity: str
) -> tuple[np.ndarray, list[tuple[int, int]]]:
    """Turn a method by dataset score matrix into per-dataset paired comparisons.

    For each dataset (a column) and each unordered method pair ``(i, j)`` with
    ``i < j``, the outcome is ``+1`` when method ``i`` is better, ``-1`` when
    method ``j`` is better, ``0`` on an exact tie, and ``nan`` when either
    method is missing on that dataset. "Better" is resolved through the metric
    polarity, so a lower-is-better metric is oriented before comparing.

    The pair order is the psychotools convention ``(0,1), (0,2), (1,2), (0,3),
    (1,3), (2,3), ...``: the second index runs outermost and the first index
    inner, so the result feeds ``psychotools::paircomp`` directly. (This
    coincides with the row-major order only up to three objects.)

    Parameters
    ----------
    matrix
        Array of shape ``(n_methods, n_datasets)`` holding one metric's scores.
    polarity
        ``"higher_is_better"`` or ``"lower_is_better"``.

    Returns
    -------
    tuple
        ``(comparisons, pairs)`` where ``comparisons`` has shape
        ``(n_datasets, n_pairs)`` with values in ``{-1, 0, 1, nan}`` and
        ``pairs`` lists the ``(i, j)`` method index pairs in column order.

    Raises
    ------
    ValueError
        If ``matrix`` is not 2D, has fewer than two methods, or ``polarity``
        is not one of the two recognised values.
    """
    if polarity not in _POLARITIES:
        raise ValueError(f"polarity must be one of {_POLARITIES}; got {polarity!r}")
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2:
        raise ValueError(f"matrix must be 2D (methods by datasets); got shape {matrix.shape}")
    n_methods, n_datasets = matrix.shape
    if n_methods < 2:
        raise ValueError("need at least 2 methods to form a comparison")

    oriented = matrix if polarity == "higher_is_better" else -matrix
    # psychotools paircomp column order: second index outermost, first inner.
    pairs = [(i, j) for j in range(n_methods) for i in range(j)]
    comparisons = np.full((n_datasets, len(pairs)), np.nan, dtype=float)
    for col, (i, j) in enumerate(pairs):
        a = oriented[i, :]
        b = oriented[j, :]
        observed = ~(np.isnan(a) | np.isnan(b))
        comparisons[observed, col] = np.sign(a[observed] - b[observed])
    return comparisons, pairs


@dataclass(frozen=True)
class BTNode:
    """One node of a fitted Bradley-Terry tree.

    Attributes
    ----------
    id
        Node id in the partykit numbering (the root is 1).
    terminal
        True for a leaf, False for an inner (split) node.
    n
        Number of datasets in the leaf, or ``None`` for an inner node.
    split_variable
        For an inner node, the feature the node splits on; ``None`` for a leaf.
    split_breakpoint
        For a numeric split, the threshold; ``None`` otherwise.
    p_values
        For an inner node, the parameter-stability test p-value per candidate
        feature; ``None`` for a leaf or when the test output was unavailable.
    worth
        For a leaf, the Bradley-Terry strengths (summing to one) aligned with
        the report's ``method_names``, with ``nan`` for a method never
        compared in the leaf; ``None`` for an inner node.
    worth_se
        Standard errors of ``worth``, same alignment; ``None`` for an inner
        node.
    """

    id: int
    terminal: bool
    n: int | None
    split_variable: str | None
    split_breakpoint: float | None
    p_values: dict[str, float] | None
    worth: np.ndarray | None
    worth_se: np.ndarray | None


@dataclass(frozen=True)
class BradleyTerryTreeReport:
    """Outcome of a Bradley-Terry tree fit on per-dataset method comparisons.

    Attributes
    ----------
    method_names
        Method labels in the order the worth arrays are aligned to (the input
        order).
    dataset_names
        Dataset labels in the order ``leaf_assignment`` is aligned to.
    nodes
        Every node of the tree, inner and terminal.
    leaf_assignment
        The terminal node id each dataset falls in, aligned with
        ``dataset_names``.
    global_worth
        Bradley-Terry strengths from a single model over all datasets, the
        reference ranking the tree qualifies, aligned with ``method_names``.
    global_worth_se
        Standard errors of ``global_worth``.
    did_split
        True when the tree found at least one feature split; False when it
        degraded to a single flat Bradley-Terry model.
    feature_names
        The candidate splitting features that were offered to the tree.
    minsize
        The minimal node size the tree was fit with.
    alpha
        The significance level used for the split test.
    warnings
        Warnings raised by psychotree during the fit.
    """

    method_names: tuple[str, ...]
    dataset_names: tuple[str, ...]
    nodes: tuple[BTNode, ...]
    leaf_assignment: tuple[int, ...]
    global_worth: np.ndarray
    global_worth_se: np.ndarray
    did_split: bool
    feature_names: tuple[str, ...]
    minsize: int
    alpha: float
    warnings: tuple[str, ...]

    @property
    def terminal_nodes(self) -> tuple[BTNode, ...]:
        """The leaf nodes, in id order."""
        return tuple(n for n in self.nodes if n.terminal)

    @property
    def inner_nodes(self) -> tuple[BTNode, ...]:
        """The split nodes, in id order."""
        return tuple(n for n in self.nodes if not n.terminal)

    def global_ranking(self) -> list[str]:
        """Method names ordered by the global Bradley-Terry strength, strongest first."""
        return self._ranking(self.global_worth)

    def node_ranking(self, node_id: int) -> list[str]:
        """Method names ordered by strength within one leaf, strongest first.

        Raises
        ------
        KeyError
            If ``node_id`` is not a terminal node.
        """
        node = self._terminal(node_id)
        return self._ranking(node.worth)

    def datasets_in_node(self, node_id: int) -> list[str]:
        """The dataset names assigned to one leaf."""
        return [
            self.dataset_names[i] for i, leaf in enumerate(self.leaf_assignment) if leaf == node_id
        ]

    def reversed_leaves(self) -> list[int]:
        """Leaf ids whose strongest method differs from the global strongest one.

        These are the subgroups where the pooled recommendation does not hold,
        the output the tree exists to surface.
        """
        global_top = self.global_ranking()[0]
        out = []
        for node in self.terminal_nodes:
            if node.worth is None or np.all(np.isnan(node.worth)):
                continue
            if self._ranking(node.worth)[0] != global_top:
                out.append(node.id)
        return out

    def summary(self) -> str:
        """A one-paragraph, plain-language reading of the tree."""
        n_datasets = len(self.dataset_names)
        gtop = self.global_ranking()[0]
        if not self.did_split:
            return (
                f"The Bradley-Terry tree found no dataset feature that splits the "
                f"method ranking at alpha {self.alpha:g} over {n_datasets} datasets, "
                f"so the ranking is reported as one Bradley-Terry model over all of "
                f"them, led by {gtop}. With this many datasets the split test has "
                f"few observations to work with, the same small-sample limit the "
                f"critical-difference diagram shows; a benchmark with more datasets "
                f"is where a split can appear."
            )
        split_vars = sorted({n.split_variable for n in self.inner_nodes if n.split_variable})
        reversed_ids = self.reversed_leaves()
        parts = [
            f"The Bradley-Terry tree splits the {n_datasets} datasets on "
            f"{', '.join(split_vars) if split_vars else 'a dataset feature'} into "
            f"{len(self.terminal_nodes)} leaves; the global ranking is led by {gtop}."
        ]
        if reversed_ids:
            phrases = []
            for nid in reversed_ids:
                leaf_top = self.node_ranking(nid)[0]
                n_members = len(self.datasets_in_node(nid))
                phrases.append(
                    f"in a leaf of {n_members} datasets the ranking is led by {leaf_top}"
                )
            parts.append(
                "The pooled recommendation does not hold everywhere: " + "; ".join(phrases) + "."
            )
        else:
            parts.append(
                f"{gtop} leads in every leaf, so the split changes the order among the "
                f"other methods but not the top choice."
            )
        return " ".join(parts)

    def _terminal(self, node_id: int) -> BTNode:
        for node in self.nodes:
            if node.id == node_id and node.terminal:
                return node
        raise KeyError(f"{node_id} is not a terminal node of this tree")

    def _ranking(self, worth: np.ndarray | None) -> list[str]:
        if worth is None:
            raise ValueError("node has no worth estimates")
        order = np.argsort(-np.where(np.isnan(worth), -np.inf, worth))
        return [self.method_names[i] for i in order]


def bradley_terry_tree(
    matrix: np.ndarray,
    method_names: Sequence[str],
    dataset_names: Sequence[str],
    numeric_features: dict[str, Sequence[float]] | None = None,
    categorical_features: dict[str, Sequence[str]] | None = None,
    polarity: str = "higher_is_better",
    minsize: int = 5,
    alpha: float = 0.05,
) -> BradleyTerryTreeReport:
    """Fit a Bradley-Terry tree on per-dataset paired method comparisons.

    Parameters
    ----------
    matrix
        Array of shape ``(n_methods, n_datasets)`` holding one metric's scores.
    method_names
        Length ``n_methods`` row labels, the objects compared.
    dataset_names
        Length ``n_datasets`` column labels, the subjects whose features split
        the tree.
    numeric_features, categorical_features
        Maps from feature name to a length ``n_datasets`` sequence of values,
        the candidate splitting variables. At least one feature across the two
        maps is required.
    polarity
        ``"higher_is_better"`` or ``"lower_is_better"``, the metric direction
        used to orient the pairwise comparisons.
    minsize
        Minimal number of datasets in a node; the tree will not create a leaf
        smaller than this.
    alpha
        Significance level for the parameter-stability split test.

    Returns
    -------
    BradleyTerryTreeReport

    Raises
    ------
    ValueError
        For shape, length, polarity, or empty-feature problems.
    RNotAvailableError
        If the R toolchain with psychotree is not available.
    RExecutionError
        If the R subprocess fails.
    """
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2:
        raise ValueError(f"matrix must be 2D (methods by datasets); got shape {matrix.shape}")
    n_methods, n_datasets = matrix.shape
    if len(method_names) != n_methods:
        raise ValueError(
            f"method_names has {len(method_names)} entries but matrix has {n_methods} rows"
        )
    if len(dataset_names) != n_datasets:
        raise ValueError(
            f"dataset_names has {len(dataset_names)} entries but matrix has {n_datasets} columns"
        )
    if n_datasets < 2:
        raise ValueError("need at least 2 datasets to fit a tree")

    numeric_features = dict(numeric_features or {})
    categorical_features = dict(categorical_features or {})
    if not numeric_features and not categorical_features:
        raise ValueError("need at least one dataset feature to split on")
    for name, values in {**numeric_features, **categorical_features}.items():
        if len(values) != n_datasets:
            raise ValueError(
                f"feature {name!r} has {len(values)} values but there are {n_datasets} datasets"
            )

    comparisons, _ = paired_comparisons(matrix, polarity)
    # JSON has no NaN; send the missing comparisons as null.
    comparison_rows = [[None if np.isnan(v) else int(v) for v in row] for row in comparisons]

    payload = {
        "objects": [str(m) for m in method_names],
        "comparisons": comparison_rows,
        "features_numeric": {k: [float(x) for x in v] for k, v in numeric_features.items()},
        "features_categorical": {k: [str(x) for x in v] for k, v in categorical_features.items()},
        "minsize": int(minsize),
        "alpha": float(alpha),
    }
    reply = run_rscript(_R_PACKAGE, _R_SCRIPT, payload, _R_PACKAGES, _FIT_TIMEOUT_SECONDS)

    method_tuple = tuple(str(m) for m in method_names)
    nodes = tuple(_node_from_reply(rec) for rec in reply["nodes"])
    return BradleyTerryTreeReport(
        method_names=method_tuple,
        dataset_names=tuple(str(d) for d in dataset_names),
        nodes=nodes,
        leaf_assignment=tuple(int(x) for x in reply["leaf_assignment"]),
        global_worth=_as_float_array(reply["global_worth"], n_methods),
        global_worth_se=_as_float_array(reply["global_worth_se"], n_methods),
        did_split=bool(reply["split"]),
        feature_names=tuple(reply["feature_names"]),
        minsize=int(reply["minsize"]),
        alpha=float(reply["alpha"]),
        warnings=tuple(reply["warnings"]) if reply["warnings"] else (),
    )


def _node_from_reply(rec: dict) -> BTNode:
    """Build a BTNode from one R node record, mapping JSON null to None or NaN."""
    worth = rec.get("worth")
    worth_se = rec.get("worth_se")
    p_values = rec.get("p_values")
    return BTNode(
        id=int(rec["id"]),
        terminal=bool(rec["terminal"]),
        n=int(rec["n"]) if rec.get("n") is not None else None,
        split_variable=rec.get("split_variable"),
        split_breakpoint=(
            float(rec["split_breakpoint"]) if rec.get("split_breakpoint") is not None else None
        ),
        p_values=(
            {k: (float(v) if v is not None else float("nan")) for k, v in p_values.items()}
            if p_values
            else None
        ),
        worth=(_nan_array(worth) if worth is not None else None),
        worth_se=(_nan_array(worth_se) if worth_se is not None else None),
    )


def _nan_array(values: Sequence) -> np.ndarray:
    """Convert a JSON list with nulls into a float array with NaN for null."""
    return np.array([np.nan if v is None else float(v) for v in values], dtype=float)


def _as_float_array(values: Sequence, n: int) -> np.ndarray:
    """Coerce a possibly-scalar JSON value into a length-n float array with NaN for null."""
    if not isinstance(values, list):
        values = [values]
    return _nan_array(values) if len(values) == n else np.full(n, np.nan)
