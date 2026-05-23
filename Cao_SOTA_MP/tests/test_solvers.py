"""Tests for graph module and solvers on a small known graph."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import networkx as nx
from src.graph import RoadNetwork
from src.generator import generate_travel_times, compute_deadline
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


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
