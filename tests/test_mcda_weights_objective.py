"""Regression tests for the objective weighting schemes.

The reference values come from pymcdm, which is imported here as a test-only
oracle and never from the beam source. pymcdm signatures are checked by
introspection first, because merec_weights takes a criteria types argument
while standard_deviation_weights and critic_weights do not.
"""

from __future__ import annotations

import inspect

import numpy as np
import pymcdm.weights as pmw
import pytest

from beam.mcda.weights import (
    critic_weights,
    merec_weights,
    standard_deviation_weights,
)

_SEEDS = (0, 1, 7, 42, 2026)
_SHAPES = ((6, 4), (10, 3), (8, 5), (3, 2))


def _random_matrix(seed: int, shape: tuple[int, int]) -> np.ndarray:
    """Return a strictly positive random matrix in (0, 1] for the given seed.

    The lower bound is kept away from zero so MEREC, which takes a logarithm
    of the normalized scores, is defined on every column.
    """
    rng = np.random.default_rng(seed)
    return rng.uniform(0.05, 1.0, size=shape)


def test_pymcdm_signatures_are_as_expected() -> None:
    """Confirm which pymcdm weight functions require a types argument."""
    std_params = inspect.signature(pmw.standard_deviation_weights).parameters
    critic_params = inspect.signature(pmw.critic_weights).parameters
    merec_params = inspect.signature(pmw.merec_weights).parameters

    assert "types" not in std_params
    assert "types" not in critic_params
    assert "types" in merec_params


@pytest.mark.parametrize("seed", _SEEDS)
@pytest.mark.parametrize("shape", _SHAPES)
def test_standard_deviation_matches_pymcdm(seed: int, shape: tuple[int, int]) -> None:
    matrix = _random_matrix(seed, shape)
    expected = pmw.standard_deviation_weights(matrix)
    got = standard_deviation_weights(matrix)
    assert np.allclose(got, expected, atol=1e-10)
    assert np.isclose(got.sum(), 1.0)
    assert np.all(got >= 0)


@pytest.mark.parametrize("seed", _SEEDS)
@pytest.mark.parametrize("shape", _SHAPES)
def test_critic_matches_pymcdm(seed: int, shape: tuple[int, int]) -> None:
    matrix = _random_matrix(seed, shape)
    expected = pmw.critic_weights(matrix)
    got = critic_weights(matrix)
    assert np.allclose(got, expected, atol=1e-10)
    assert np.isclose(got.sum(), 1.0)
    assert np.all(got >= 0)


@pytest.mark.parametrize("seed", _SEEDS)
@pytest.mark.parametrize("shape", _SHAPES)
def test_merec_matches_pymcdm(seed: int, shape: tuple[int, int]) -> None:
    matrix = _random_matrix(seed, shape)
    n_metrics = shape[1]
    all_profit = np.ones(n_metrics)
    expected = pmw.merec_weights(matrix, all_profit)
    got = merec_weights(matrix)
    assert np.allclose(got, expected, atol=1e-10)
    assert np.isclose(got.sum(), 1.0)
    assert np.all(got >= 0)


def test_standard_deviation_zero_variation_falls_back_to_equal() -> None:
    matrix = np.full((5, 4), 0.3)
    got = standard_deviation_weights(matrix)
    assert np.allclose(got, np.full(4, 0.25))


def test_critic_zero_variation_falls_back_to_equal() -> None:
    matrix = np.full((5, 4), 0.3)
    got = critic_weights(matrix)
    assert np.allclose(got, np.full(4, 0.25))


def test_merec_zero_variation_falls_back_to_equal() -> None:
    # Every column constant means dropping any column leaves the aggregate
    # unchanged, so every removal effect is zero and the fallback triggers.
    matrix = np.full((5, 4), 0.3)
    got = merec_weights(matrix)
    assert np.allclose(got, np.full(4, 0.25))


def test_merec_rejects_zero_values() -> None:
    matrix = np.array([[0.0, 0.5], [0.5, 0.5], [0.7, 0.2]])
    with pytest.raises(ValueError, match="logarithm"):
        merec_weights(matrix)


def test_objective_weights_reject_negative_values() -> None:
    matrix = np.array([[0.5, -0.1], [0.2, 0.3], [0.4, 0.6]])
    for func in (standard_deviation_weights, critic_weights, merec_weights):
        with pytest.raises(ValueError, match="non-negative"):
            func(matrix)


def test_objective_weights_reject_single_tool() -> None:
    matrix = np.array([[0.5, 0.2, 0.9]])
    for func in (standard_deviation_weights, critic_weights, merec_weights):
        with pytest.raises(ValueError, match="at least 2 tools"):
            func(matrix)
