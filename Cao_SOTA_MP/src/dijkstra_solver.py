"""Dijkstra baseline solver for the punctuality problem."""

import numpy as np
import networkx as nx
from .graph import RoadNetwork


def solve_dijkstra(network: RoadNetwork, W: np.ndarray, origin: int, destination: int,
                   tau: float) -> dict:
    """Find shortest path by average travel time, then compute its punctuality.

    Args:
        network: Road network
        W: Travel time samples (N x |L|)
        origin: Origin node
        destination: Destination node
        tau: Deadline

    Returns:
        dict with keys: path_x, punctuality_prob, status, solve_time
    """
    import time
    t0 = time.perf_counter()

    N, num_edges = W.shape
    mean_weights = W.mean(axis=0)

    # Set edge weights
    G = network.graph.copy()
    for j, (u, v) in enumerate(network.edges):
        G[u][v]["weight"] = mean_weights[j]

    # Dijkstra
    try:
        path = nx.shortest_path(G, origin, destination, weight="weight")
    except nx.NetworkXNoPath:
        return {"path_x": None, "punctuality_prob": None,
                "status": "NoPath", "solve_time": time.perf_counter() - t0}

    path_x = network.path_to_x(path)

    # Compute punctuality
    path_travel_times = W @ path_x
    lateness_count = np.sum(path_travel_times > tau)
    punctuality_prob = 1.0 - lateness_count / N

    return {
        "path_x": path_x,
        "punctuality_prob": punctuality_prob,
        "status": "Optimal",
        "solve_time": time.perf_counter() - t0,
    }
