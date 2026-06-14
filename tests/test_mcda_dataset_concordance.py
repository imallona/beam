"""Tests for beam.mcda.dataset_concordance."""

import numpy as np
import pytest

from beam.mcda import dataset_concordance


def _three_dataset_tensor():
    """Two datasets that order three tools the same, one that reverses them.

    Single metric, higher is better. Dataset 0 and 1 both rank tool 0 first and
    tool 2 last; dataset 2 reverses that order.
    """
    return np.array(
        [
            [[0.9], [0.8], [0.1]],
            [[0.5], [0.4], [0.5]],
            [[0.1], [0.2], [0.9]],
        ]
    )


def test_agreement_matrix_and_mean():
    report = dataset_concordance(_three_dataset_tensor(), ["higher_is_better"])
    assert report.evaluated_datasets == (0, 1, 2)
    tau = report.tau_matrix
    assert tau.shape == (3, 3)
    assert np.allclose(np.diag(tau), 1.0)
    assert tau[0, 1] == pytest.approx(1.0)
    assert tau[0, 2] == pytest.approx(-1.0)
    assert tau[1, 2] == pytest.approx(-1.0)
    assert report.mean_pairwise_tau == pytest.approx(-1.0 / 3.0)


def test_most_idiosyncratic_is_the_reversed_dataset():
    report = dataset_concordance(_three_dataset_tensor(), ["higher_is_better"])
    assert report.most_idiosyncratic_dataset == 2
    assert report.per_dataset_mean_tau[2] == pytest.approx(-1.0)


def test_concordant_grouping():
    report = dataset_concordance(_three_dataset_tensor(), ["higher_is_better"], threshold=0.5)
    assert report.concordant_groups == ((0, 1), (2,))


def test_notable_cells_locate_the_disagreement():
    report = dataset_concordance(_three_dataset_tensor(), ["higher_is_better"])
    # Tools 0 and 2 each move a full rank on dataset 2 relative to their mean.
    moved = {(cell.tool, cell.dataset) for cell in report.notable_cells}
    assert (0, 2) in moved
    assert (2, 2) in moved
    # Tool 1 is rank 2 on every dataset, so it never deviates.
    assert all(cell.tool != 1 for cell in report.notable_cells)
    deviations = [abs(cell.deviation) for cell in report.notable_cells]
    assert deviations == sorted(deviations, reverse=True)


def test_unrankable_dataset_is_dropped():
    tensor = _three_dataset_tensor().copy()
    tensor[1, 1, 0] = np.nan  # dataset 1 now has a missing cell
    report = dataset_concordance(tensor, ["higher_is_better"], missing="error")
    assert report.evaluated_datasets == (0, 2)
    assert report.tau_matrix.shape == (2, 2)


def test_rank_deviation_shape_and_sign():
    report = dataset_concordance(_three_dataset_tensor(), ["higher_is_better"])
    assert report.rank_deviation.shape == (3, 3)
    # Tool 0 places higher than its mean on datasets 0 and 1 (negative deviation).
    pos0 = report.evaluated_datasets.index(0)
    assert report.rank_deviation[0, pos0] < 0


def test_validation_errors():
    with pytest.raises(ValueError, match="3D"):
        dataset_concordance(np.zeros((3, 2)), ["higher_is_better"])
    with pytest.raises(ValueError, match="at least 2 datasets"):
        dataset_concordance(np.zeros((3, 1, 1)), ["higher_is_better"])
    with pytest.raises(ValueError, match="polarity"):
        dataset_concordance(np.zeros((3, 2, 2)), ["higher_is_better"])


def test_too_few_rankable_datasets_raises():
    tensor = _three_dataset_tensor().copy()
    tensor[0, 1, 0] = np.nan
    tensor[0, 2, 0] = np.nan
    with pytest.raises(ValueError, match="at least two datasets that produce a ranking"):
        dataset_concordance(tensor, ["higher_is_better"], missing="error")


def test_runresult_carries_concordance():
    import beam

    tensor = _three_dataset_tensor()
    scores = beam.Scores(
        values=tensor,
        tool_names=("a", "b", "c"),
        metric_ids=("ari",),
        dataset_names=("d0", "d1", "d2"),
        layout="long",
    )
    result = beam.rank(scores, sensitivity=False)
    assert result.dataset_concordance is not None
    assert result.dataset_concordance.dataset_names == ("d0", "d1", "d2")
