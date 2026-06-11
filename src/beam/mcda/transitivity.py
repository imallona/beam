"""Check whether the pairwise majority relation gives one consistent order.

Each aggregation in ``beam.mcda`` returns one ordering of the methods. That
ordering agrees with the pairwise evidence only when the pairwise majority
relation is transitive. It is not always transitive. Method A can outperform B on
most of the datasets they share, B outperform C, and C outperform A. Those three
results form a cycle, and when a cycle is present no single ordering agrees with
all the pairwise majorities. Condorcet described such cycles in his 1785 essay on
majority voting, along with the case of an option preferred to every other option
in pairwise comparison.

``pairwise_transitivity`` reads a ``PairwiseSuperiorityReport`` and builds the
pairwise majority relation from its outperformance counts. Those counts already
apply the region of practical equivalence, so a difference inside the noise floor
is not counted as an outperformance. The function reports the method preferred to
every other one when such a method exists, the cyclic triples of methods, the
coefficient of consistence of Kendall and Babington Smith (1940), and whether the
relation is transitive.

It runs no new ranking. It reads a relation ``pairwise_superiority`` already
computed and reports whether one ordering is consistent with it, in the same way
``specification_curve`` reports on the grid ``rank_sensitivity`` already ran.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np

from .pairwise import PairwiseSuperiorityReport


@dataclass(frozen=True)
class PairwiseTransitivityReport:
    """The consistency of the pairwise majority relation over the methods.

    Attributes
    ----------
    method_names
        Method labels in index order, or ``None`` when none were given.
    dominance
        ``(n_methods, n_methods)`` int matrix. Entry ``[i, j]`` is 1 when method
        ``i`` outperforms method ``j`` on more of their shared datasets than the
        reverse. The diagonal is 0, and a tied pair leaves both ``[i, j]`` and
        ``[j, i]`` at 0.
    tied_pairs
        Unordered pairs with no majority preference: the two methods outperform
        each other on the same number of shared datasets, or share no decisive
        dataset. These pairs carry no edge.
    condorcet_choice
        The method index preferred to every other method by pairwise majority, or
        ``None`` when no such method exists. It must be preferred to each other
        method outright; a tie against any method rules it out.
    circular_triads
        Every set of three methods whose edges form a cycle: each of the three
        outperforms one of the other two and is outperformed by the third. Each is
        a tuple of the three method indices in ascending order. Only a triple whose
        three pairs are all decided can be cyclic.
    n_circular_triads
        The number of circular triads.
    n_triads
        The number of method triples, ``C(n_methods, 3)``, the denominator for the
        circular-triad count.
    coefficient_of_consistence
        Kendall and Babington Smith's (1940) coefficient of consistence in
        ``[0, 1]``: ``1 - d / d_max``, where ``d`` is the circular-triad count and
        ``d_max`` is the largest number of circular triads a relation of this size
        can hold. A value of 1 is a transitive relation and 0 is the least
        consistent relation. ``None`` when any pair is tied, since the coefficient
        is defined only when every pair is decided.
    is_transitive
        ``True`` when the relation has no transitivity break: whenever ``i``
        outperforms ``j`` and ``j`` outperforms ``k``, ``i`` outperforms ``k``.
    consistent_order
        The single method order implied by the relation, best first, when every
        pair is decided and the relation is transitive. ``None`` otherwise, which
        includes the case where ties leave the order undetermined and the case of a
        cycle.
    n_methods
        The number of methods.
    rope
        The region of practical equivalence carried over from the superiority
        report, in native units. An edge counts an outperformance only past this
        band.
    summary
        A short plain-language reading of the relation.
    """

    method_names: tuple[str, ...] | None
    dominance: np.ndarray
    tied_pairs: tuple[tuple[int, int], ...]
    condorcet_choice: int | None
    circular_triads: tuple[tuple[int, int, int], ...]
    n_circular_triads: int
    n_triads: int
    coefficient_of_consistence: float | None
    is_transitive: bool
    consistent_order: tuple[int, ...] | None
    n_methods: int
    rope: float
    summary: str


def pairwise_transitivity(report: PairwiseSuperiorityReport) -> PairwiseTransitivityReport:
    """Test the pairwise majority relation for one consistent order.

    Reads a ``PairwiseSuperiorityReport`` and builds the pairwise majority
    relation from its per-pair outperformance counts: method ``i`` outperforms
    ``j`` when it does so on more of their shared datasets than ``j`` does. Those
    counts already apply the region of practical equivalence, so a difference
    inside the noise floor adds no edge. The relation is then checked for a method
    preferred to all others, for circular triads, and for transitivity, and the
    coefficient of consistence is reported when every pair is decided.

    Parameters
    ----------
    report
        A ``PairwiseSuperiorityReport`` from ``beam.mcda.pairwise_superiority``.

    Returns
    -------
    PairwiseTransitivityReport

    Examples
    --------
    >>> import numpy as np
    >>> from beam.mcda import pairwise_superiority, pairwise_transitivity
    >>> scores = np.array([[0.9, 0.8, 0.7], [0.5, 0.6, 0.4], [0.2, 0.1, 0.3]])
    >>> sup = pairwise_superiority(scores, "higher_is_better")
    >>> cc = pairwise_transitivity(sup)
    >>> cc.condorcet_choice
    0
    >>> cc.is_transitive
    True
    >>> cc.n_circular_triads
    0
    """
    n = report.probability_superior.shape[0]
    names = report.method_names

    dominance = np.zeros((n, n), dtype=int)
    tied_pairs: list[tuple[int, int]] = []
    for pair in report.per_pair:
        if pair.a_outperforms > pair.b_outperforms:
            dominance[pair.a, pair.b] = 1
        elif pair.b_outperforms > pair.a_outperforms:
            dominance[pair.b, pair.a] = 1
        else:
            tied_pairs.append((pair.a, pair.b))

    every_pair_decided = len(tied_pairs) == 0

    circular_triads: list[tuple[int, int, int]] = []
    for triple in combinations(range(n), 3):
        block = dominance[np.ix_(triple, triple)]
        if block.sum() == 3 and block.sum(axis=1).tolist() == [1, 1, 1]:
            circular_triads.append(triple)
    n_triads = n * (n - 1) * (n - 2) // 6

    coefficient_of_consistence = None
    if every_pair_decided:
        d_max = (n**3 - n) / 24 if n % 2 else (n**3 - 4 * n) / 24
        coefficient_of_consistence = (
            1.0 if d_max == 0 else float(1.0 - len(circular_triads) / d_max)
        )

    is_transitive = _is_transitive(dominance)

    condorcet_choice = None
    for i in range(n):
        if all(dominance[i, j] == 1 for j in range(n) if j != i):
            condorcet_choice = i
            break

    consistent_order = None
    if every_pair_decided and is_transitive:
        consistent_order = tuple(int(i) for i in np.argsort(-dominance.sum(axis=1), kind="stable"))

    summary = _summary(
        names,
        condorcet_choice,
        len(circular_triads),
        n_triads,
        coefficient_of_consistence,
        is_transitive,
        len(tied_pairs),
        consistent_order,
    )

    return PairwiseTransitivityReport(
        method_names=names,
        dominance=dominance,
        tied_pairs=tuple(tied_pairs),
        condorcet_choice=condorcet_choice,
        circular_triads=tuple(circular_triads),
        n_circular_triads=len(circular_triads),
        n_triads=n_triads,
        coefficient_of_consistence=coefficient_of_consistence,
        is_transitive=is_transitive,
        consistent_order=consistent_order,
        n_methods=n,
        rope=report.rope,
        summary=summary,
    )


def _is_transitive(dominance: np.ndarray) -> bool:
    """Whether ``i`` over ``j`` and ``j`` over ``k`` always implies ``i`` over ``k``."""
    n = dominance.shape[0]
    for i in range(n):
        for j in range(n):
            if not dominance[i, j]:
                continue
            for k in range(n):
                if dominance[j, k] and not dominance[i, k]:
                    return False
    return True


def _name(names: tuple[str, ...] | None, i: int) -> str:
    return names[i] if names is not None else f"method {i}"


def _summary(
    names: tuple[str, ...] | None,
    condorcet_choice: int | None,
    n_circular_triads: int,
    n_triads: int,
    coefficient_of_consistence: float | None,
    is_transitive: bool,
    n_tied_pairs: int,
    consistent_order: tuple[int, ...] | None,
) -> str:
    parts: list[str] = []
    if condorcet_choice is not None:
        parts.append(
            f"{_name(names, condorcet_choice)} is preferred to every other method by pairwise "
            "majority"
        )
    else:
        parts.append("no method is preferred to every other method by pairwise majority")

    if n_circular_triads == 0 and is_transitive:
        if consistent_order is not None:
            order = ", ".join(_name(names, i) for i in consistent_order)
            parts.append(
                "the relation is transitive and every pair is decided, so one order is "
                f"consistent with it: {order}"
            )
        else:
            parts.append(
                f"the relation is transitive but {n_tied_pairs} pairs are tied, so it gives a "
                "partial order rather than one full order"
            )
    else:
        plural = "" if n_circular_triads == 1 else "s"
        parts.append(
            f"the relation has {n_circular_triads} circular triad{plural} out of {n_triads}, so it "
            "is not transitive and no single order agrees with all the pairwise majorities"
        )

    if coefficient_of_consistence is not None:
        parts.append(f"the coefficient of consistence is {coefficient_of_consistence:.2f}")
    elif n_tied_pairs:
        parts.append("the coefficient of consistence is not defined because some pairs are tied")

    return ". ".join(p[0].upper() + p[1:] for p in parts) + "."
