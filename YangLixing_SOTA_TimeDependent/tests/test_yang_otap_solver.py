"""Tests for the Yang time-dependent OTAP ILP core solver."""

from pathlib import Path
import sys

import networkx as nx
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from Cao_SOTA_MP.src.graph import RoadNetwork
from YangLixing_SOTA_TimeDependent.src import duration_to_time_steps, solve_yang_otap_ilp


def make_two_path_network() -> RoadNetwork:
    graph = nx.DiGraph()
    graph.add_edges_from([(0, 1), (1, 3), (0, 2), (2, 3)])
    return RoadNetwork.from_networkx(graph)


def enumerate_path_times(
    network: RoadNetwork,
    travel_times: np.ndarray,
    path: list[int],
    time_step: float,
) -> np.ndarray:
    times = []
    for sample_idx in range(travel_times.shape[0]):
        t_idx = 0
        elapsed = 0.0
        feasible = True
        for u, v in zip(path[:-1], path[1:]):
            edge_idx = network.edge_index((u, v))
            if t_idx >= travel_times.shape[1]:
                feasible = False
                break
            steps = duration_to_time_steps(travel_times[sample_idx, t_idx, edge_idx], time_step)
            t_idx += steps
            elapsed += steps * time_step
            if t_idx > travel_times.shape[1]:
                feasible = False
                break
        times.append(elapsed if feasible else np.inf)
    return np.array(times, dtype=np.float64)


def test_duration_to_time_steps_rounds_up_and_validates_inputs():
    assert duration_to_time_steps(0.1, 1.0) == 1
    assert duration_to_time_steps(1.0, 1.0) == 1
    assert duration_to_time_steps(1.01, 1.0) == 2
    assert duration_to_time_steps(2.0, 0.5) == 4

    with pytest.raises(ValueError, match="duration must be positive"):
        duration_to_time_steps(0.0, 1.0)
    with pytest.raises(ValueError, match="time_step must be positive"):
        duration_to_time_steps(1.0, 0.0)


def test_yang_otap_ilp_matches_manual_enumeration_on_minimal_time_dependent_data():
    network = make_two_path_network()
    edge_01 = network.edge_index((0, 1))
    edge_13 = network.edge_index((1, 3))
    edge_02 = network.edge_index((0, 2))
    edge_23 = network.edge_index((2, 3))

    td = np.full((3, 5, network.num_edges), 9.0, dtype=np.float64)
    # Path 0-1-3 arrives on time in samples 0 and 1, late in sample 2.
    td[0, 0, edge_01] = 1.0
    td[0, 1, edge_13] = 1.0
    td[1, 0, edge_01] = 1.0
    td[1, 1, edge_13] = 1.0
    td[2, 0, edge_01] = 2.0
    td[2, 2, edge_13] = 2.0

    # Path 0-2-3 arrives on time only in sample 2.
    td[0, 0, edge_02] = 2.0
    td[0, 2, edge_23] = 2.0
    td[1, 0, edge_02] = 2.0
    td[1, 2, edge_23] = 2.0
    td[2, 0, edge_02] = 1.0
    td[2, 1, edge_23] = 1.0

    tau = 2.0
    result = solve_yang_otap_ilp(
        network=network,
        travel_times=td,
        origin=0,
        destination=3,
        tau=tau,
        time_step=1.0,
        solver_name="CBC",
        time_limit=10,
    )

    path_a_times = enumerate_path_times(network, td, [0, 1, 3], 1.0)
    path_b_times = enumerate_path_times(network, td, [0, 2, 3], 1.0)
    path_a_prob = float(np.mean(path_a_times <= tau))
    path_b_prob = float(np.mean(path_b_times <= tau))

    assert result["status"] == "Optimal"
    assert result["path_edges"] == [(0, 1), (1, 3)]
    assert result["punctuality_prob"] == pytest.approx(max(path_a_prob, path_b_prob))
    assert result["punctuality_prob"] == pytest.approx(2 / 3)
    assert result["on_time_count"] == 2
    assert result["lateness_count"] == 1
    assert np.allclose(result["sample_travel_times"], path_a_times)
    assert result["arrival_time_indices"].tolist() == [2, 2, 4]
    assert "Yang_OTAP_ILP found path" in result["conclusion"]


def test_yang_otap_ilp_supports_sample_probabilities():
    network = make_two_path_network()
    edge_01 = network.edge_index((0, 1))
    edge_13 = network.edge_index((1, 3))
    edge_02 = network.edge_index((0, 2))
    edge_23 = network.edge_index((2, 3))

    td = np.full((2, 4, network.num_edges), 9.0, dtype=np.float64)
    # Path A on time for low-probability sample 0 only.
    td[0, 0, edge_01] = 1.0
    td[0, 1, edge_13] = 1.0
    td[1, 0, edge_01] = 2.0
    td[1, 2, edge_13] = 2.0
    # Path B on time for high-probability sample 1 only.
    td[0, 0, edge_02] = 2.0
    td[0, 2, edge_23] = 2.0
    td[1, 0, edge_02] = 1.0
    td[1, 1, edge_23] = 1.0

    result = solve_yang_otap_ilp(
        network=network,
        travel_times=td,
        origin=0,
        destination=3,
        tau=2.0,
        sample_probabilities=np.array([0.1, 0.9]),
        solver_name="CBC",
        time_limit=10,
    )

    assert result["status"] == "Optimal"
    assert result["path_edges"] == [(0, 2), (2, 3)]
    assert result["punctuality_prob"] == pytest.approx(0.9)
    assert result["on_time_count"] == 1
    assert result["lateness_count"] == 1


def test_yang_otap_ilp_rejects_invalid_tensor_shape():
    network = make_two_path_network()
    with pytest.raises(ValueError, match="travel_times must be 3D"):
        solve_yang_otap_ilp(
            network=network,
            travel_times=np.ones((2, network.num_edges)),
            origin=0,
            destination=3,
            tau=2.0,
        )
