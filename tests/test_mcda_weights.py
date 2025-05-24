"""Tests for MCDA weight vectors."""

import numpy as np
import pytest

from beam.mcda import equal_weights


def test_equal_weights_sum_to_one():
    w = equal_weights(5)
    assert w.shape == (5,)
    np.testing.assert_allclose(w.sum(), 1.0)


def test_equal_weights_uniform():
    w = equal_weights(4)
    np.testing.assert_allclose(w, [0.25, 0.25, 0.25, 0.25])


def test_equal_weights_zero_raises():
    with pytest.raises(ValueError):
        equal_weights(0)
