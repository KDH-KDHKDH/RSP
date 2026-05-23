"""Artificial road network and travel time data generation."""

import numpy as np
import networkx as nx
from .graph import RoadNetwork


def generate_connected_digraph(num_nodes: int, num_edges: int, seed: int = 42) -> nx.DiGraph:
    """Generate a random connected directed graph with specified nodes and edges."""
    rng = np.random.default_rng(seed)
    G = nx.DiGraph()
    G.add_nodes_from(range(num_nodes))

    # First ensure connectivity: create a random spanning tree
    nodes = list(range(num_nodes))
    rng.shuffle(nodes)
    for i in range(num_nodes - 1):
        u, v = nodes[i], nodes[i + 1]
        if rng.random() < 0.5:
            G.add_edge(u, v)
        else:
            G.add_edge(v, u)

    # Add remaining edges randomly
    remaining = num_edges - G.number_of_edges()
    all_possible = [(u, v) for u in range(num_nodes) for v in range(num_nodes)
                    if u != v and not G.has_edge(u, v)]
    rng.shuffle(all_possible)
    for u, v in all_possible[:remaining]:
        G.add_edge(u, v)

    return G


def generate_travel_times(num_edges: int, num_samples: int,
                          time_range: tuple[float, float] = (10.0, 100.0),
                          seed: int = 42) -> np.ndarray:
    """Generate travel time samples W (N x |L|).

    Each edge gets a lognormal distribution with random mean and moderate CV.
    Returns matrix where W[i, j] = travel time of sample i on edge j.
    """
    rng = np.random.default_rng(seed)
    lo, hi = time_range
    W = np.zeros((num_samples, num_edges), dtype=np.float64)

    for j in range(num_edges):
        mean_time = rng.uniform(lo, hi)
        std_time = mean_time * rng.uniform(0.5, 1.2)
        sigma2 = np.log(1 + (std_time / mean_time) ** 2)
        mu = np.log(mean_time) - sigma2 / 2
        sigma = np.sqrt(sigma2)
        W[:, j] = rng.lognormal(mu, sigma, size=num_samples)

    return W


def compute_deadline(W: np.ndarray, network: RoadNetwork,
                     origin: int, destination: int, alpha: float,
                     paths: list[list[int]] | None = None) -> float:
    """Compute deadline: tau = tau_1 + alpha * (tau_2 - tau_1).

    tau_2 = min over all paths of (max travel time on that path)
    tau_1 = min travel time on the path that achieves tau_2
    """
    if paths is None:
        mean_weights = W.mean(axis=0)
        G = network.graph.copy()
        for j, (u, v) in enumerate(network.edges):
            G[u][v]["weight"] = mean_weights[j]
        try:
            paths = list(nx.shortest_simple_paths(G, origin, destination, weight="weight"))
            paths = paths[:200]
        except nx.NetworkXNoPath:
            return float(W.mean() * 3)

    best_tau2 = np.inf
    best_tau1 = 0.0

    for path in paths:
        x = network.path_to_x(path)
        path_times = W @ x
        max_time = path_times.max()
        min_time = path_times.min()

        if max_time < best_tau2:
            best_tau2 = max_time
            best_tau1 = min_time

    tau = best_tau1 + alpha * (best_tau2 - best_tau1)
    return tau


def random_od_pairs(network: RoadNetwork, num_pairs: int, seed: int = 42) -> list[tuple[int, int]]:
    """Generate random OD pairs that have at least one path between them."""
    rng = np.random.default_rng(seed)
    pairs = []
    nodes = network.nodes
    attempts = 0
    while len(pairs) < num_pairs and attempts < num_pairs * 100:
        o = rng.choice(nodes)
        d = rng.choice(nodes)
        if o != d and nx.has_path(network.graph, o, d):
            if (o, d) not in pairs:
                pairs.append((o, d))
        attempts += 1
    return pairs


def create_artificial_network(num_nodes: int = 65, num_edges: int = 123,
                              seed: int = 42) -> RoadNetwork:
    """Create an artificial road network matching paper specs."""
    G = generate_connected_digraph(num_nodes, num_edges, seed)
    return RoadNetwork.from_networkx(G)
