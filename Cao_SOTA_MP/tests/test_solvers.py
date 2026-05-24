"""Tests for graph module and solvers on a small known graph."""

import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import networkx as nx
import yaml
from src.graph import RoadNetwork
from src.generator import compute_deadline, generate_candidate_paths, generate_travel_times
from src import experiment as experiment_mod
from src.ilp_solver import solve_ilp
from src.milp_solver import solve_milp
from src.dijkstra_solver import solve_dijkstra


def make_small_network():
    """Create a 5-node graph with known structure for testing.

    Graph:  0 → 1 → 3 → 4
            0 → 2 → 3 → 4
            (two paths from 0 to 4)
    """
    G = nx.DiGraph()
    G.add_edges_from([(0, 1), (1, 3), (0, 2), (2, 3), (3, 4)])
    return RoadNetwork.from_networkx(G)


class TestGraph:
    def test_incidence_matrix_shape(self):
        net = make_small_network()
        M = net.incidence_matrix()
        assert M.shape == (5, 5)  # 5 nodes, 5 edges

    def test_incidence_matrix_row_sum(self):
        net = make_small_network()
        M = net.incidence_matrix()
        # Each column sums to 0 (one +1 and one -1)
        assert np.allclose(M.sum(axis=0), 0)

    def test_od_vector(self):
        net = make_small_network()
        b = net.od_vector(0, 4)
        assert b[net.node_index(0)] == 1.0
        assert b[net.node_index(4)] == -1.0
        assert b.sum() == 0.0

    def test_path_to_x(self):
        net = make_small_network()
        path = [0, 1, 3, 4]
        x = net.path_to_x(path)
        assert x.sum() == 3  # 3 edges in path

    def test_flow_conservation(self):
        """Mx = b should hold for any valid path."""
        net = make_small_network()
        M = net.incidence_matrix()
        b = net.od_vector(0, 4)
        path = [0, 2, 3, 4]
        x = net.path_to_x(path)
        assert np.allclose(M @ x, b)

    def test_enumerate_paths(self):
        net = make_small_network()
        paths = net.enumerate_paths(0, 4)
        assert len(paths) == 2  # two paths: 0-1-3-4 and 0-2-3-4


class TestSolvers:
    def setup_method(self):
        self.net = make_small_network()
        # Deterministic travel times: path 0-1-3-4 is faster on average
        # but path 0-2-3-4 is more reliable (less variance)
        np.random.seed(42)
        N = 20
        W = np.zeros((N, 5))
        # Edge 0→1: fast but variable (mean=10, std=8)
        W[:, self.net.edge_index((0, 1))] = np.random.lognormal(2.0, 0.7, N)
        # Edge 1→3: fast but variable
        W[:, self.net.edge_index((1, 3))] = np.random.lognormal(2.0, 0.7, N)
        # Edge 0→2: slower but stable (mean=12, std=2)
        W[:, self.net.edge_index((0, 2))] = np.random.lognormal(2.4, 0.15, N)
        # Edge 2→3: slower but stable
        W[:, self.net.edge_index((2, 3))] = np.random.lognormal(2.4, 0.15, N)
        # Edge 3→4: same for both paths
        W[:, self.net.edge_index((3, 4))] = np.random.lognormal(2.0, 0.3, N)
        self.W = W
        self.N = N

    def test_ilp_returns_optimal(self):
        """ILP should find the path with maximum punctuality."""
        tau = 35.0  # tight deadline
        result = solve_ilp(self.net, self.W, 0, 4, tau)
        assert result["status"] == "Optimal"
        assert result["path_x"] is not None

        # Verify by enumeration
        best_prob = -1
        for path in self.net.enumerate_paths(0, 4):
            x = self.net.path_to_x(path)
            times = self.W @ x
            prob = 1.0 - np.sum(times > tau) / self.N
            best_prob = max(best_prob, prob)

        assert abs(result["punctuality_prob"] - best_prob) < 1e-9

    def test_milp_runs(self):
        """MILP should return a valid solution."""
        tau = 35.0
        result = solve_milp(self.net, self.W, 0, 4, tau)
        assert result["status"] == "Optimal"
        assert 0 <= result["punctuality_prob"] <= 1

    def test_dijkstra_runs(self):
        """Dijkstra should return a valid solution."""
        tau = 35.0
        result = solve_dijkstra(self.net, self.W, 0, 4, tau)
        assert result["status"] == "Optimal"
        assert 0 <= result["punctuality_prob"] <= 1

    def test_ilp_beats_or_ties_others(self):
        """ILP punctuality should be >= MILP and Dijkstra."""
        tau = 35.0
        ilp = solve_ilp(self.net, self.W, 0, 4, tau)
        milp = solve_milp(self.net, self.W, 0, 4, tau)
        dij = solve_dijkstra(self.net, self.W, 0, 4, tau)

        assert ilp["punctuality_prob"] >= milp["punctuality_prob"] - 1e-9
        assert ilp["punctuality_prob"] >= dij["punctuality_prob"] - 1e-9


class TestDeadlineHeuristics:
    def setup_method(self):
        self.net = make_small_network()
        self.path_a = [0, 1, 3, 4]
        self.path_b = [0, 2, 3, 4]

        # Path A is faster on average but has a worse single-sample tail.
        self.W = np.zeros((3, self.net.num_edges))
        self.W[:, self.net.edge_index((0, 1))] = [8.0, 7.0, 30.0]
        self.W[:, self.net.edge_index((1, 3))] = [8.0, 7.0, 30.0]
        self.W[:, self.net.edge_index((0, 2))] = [12.0, 13.0, 14.0]
        self.W[:, self.net.edge_index((2, 3))] = [12.0, 13.0, 14.0]
        self.W[:, self.net.edge_index((3, 4))] = [6.0, 6.0, 6.0]

    def test_compute_deadline_uses_minimax_path(self):
        tau, diag = compute_deadline(
            self.W,
            self.net,
            0,
            4,
            alpha=0.5,
            paths=[self.path_a, self.path_b],
            return_diagnostics=True,
        )

        # Path A times: 22, 20, 66 -> max 66
        # Path B times: 30, 32, 34 -> max 34, min 30
        expected_tau = 30.0 + 0.5 * (34.0 - 30.0)
        assert tau == expected_tau
        assert diag["candidate_count"] == 2
        assert diag["T_min"] == 30.0
        assert diag["T_max"] == 34.0
        assert diag["tau"] == expected_tau

    def test_generate_candidate_paths_deduplicates_sources(self):
        paths = generate_candidate_paths(
            self.W,
            self.net,
            0,
            4,
            max_paths=10,
            seed=42,
        )

        assert len(paths) == 2
        assert {tuple(path) for path in paths} == {tuple(self.path_a), tuple(self.path_b)}

    def test_compute_deadline_exact_mode_enumerates_paths(self):
        tau, diag = compute_deadline(
            self.W,
            self.net,
            0,
            4,
            alpha=0.5,
            mode="exact",
            enumeration_cutoff=4,
            return_diagnostics=True,
        )

        assert tau == 32.0
        assert diag["candidate_count"] == 2
        assert diag["mode"] == "exact"


def test_run_experiment_keeps_nonoptimal_ilp_jobs(tmp_path):
    net = make_small_network()
    data_dir = tmp_path / "toy_data"
    data_dir.mkdir()
    net.save(data_dir / "network.npz")
    np.save(data_dir / "od_pairs.npy", np.array([(0, 4)], dtype=np.int32))
    W = np.ones((3, net.num_edges), dtype=np.float64)
    np.savez(data_dir / "travel_times.npz", repeat_00=W)
    with open(data_dir / "meta.yaml", "w") as f:
        yaml.safe_dump({"num_repeats": 1, "num_od_pairs": 1, "num_samples": 3}, f)

    config = {
        "experiment": {"num_repeats": 1, "num_od_pairs": 1, "alphas": [0.5]},
        "solver": {"backend": "CBC", "big_m": 1e6, "time_limit": 1},
        "candidate_paths": {"max_paths": 10},
        "deadline": {"mode": "exact", "enumeration_cutoff": 4},
    }

    with (
        patch.object(
            experiment_mod,
            "compute_deadline",
            return_value=(10.0, {"candidate_count": 2, "T_min": 8.0, "T_max": 12.0, "tau": 10.0, "candidate_puncts": [], "mode": "exact"}),
        ),
        patch.object(
            experiment_mod,
            "solve_ilp",
            return_value={
                "path_x": None,
                "lateness_count": None,
                "punctuality_prob": None,
                "status": "TimeLimit",
                "solve_time": 1.0,
            },
        ),
        patch.object(
            experiment_mod,
            "solve_milp",
            return_value={
                "path_x": net.path_to_x([0, 1, 3, 4]),
                "lateness_count": 0,
                "punctuality_prob": 1.0,
                "status": "Optimal",
                "solve_time": 0.1,
            },
        ),
        patch.object(
            experiment_mod,
            "solve_dijkstra",
            return_value={
                "path_x": net.path_to_x([0, 2, 3, 4]),
                "lateness_count": 0,
                "punctuality_prob": 1.0,
                "status": "Optimal",
                "solve_time": 0.001,
            },
        ),
    ):
        df = experiment_mod.run_experiment(config, data_dir=data_dir)

    assert len(df) == 3
    assert set(df["method"]) == {"ILP", "MILP", "Dijkstra"}
    assert df["reference_available"].eq(False).all()
    assert set(df["reference_status"]) == {"TimeLimit"}
    assert df["correct"].isna().all()
    assert df["objective_gap"].isna().all()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
