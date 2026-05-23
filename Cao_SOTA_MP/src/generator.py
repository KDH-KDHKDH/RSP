"""Artificial road network and travel time data generation."""

import numpy as np
import networkx as nx
from .graph import RoadNetwork
from .osm_network import get_highway_cv_range


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
                     paths: list[list[int]] | None = None,
                     max_candidate_paths: int = 1000,
                     seed: int = 42,
                     verbose: bool = False,
                     return_diagnostics: bool = False) -> float | tuple[float, dict]:
    """Compute deadline: tau = T_min + alpha * (T_max - T_min).

    T_max = min over candidate paths of (max travel time on that path)
    T_min = min travel time on the path that achieves T_max

    The minimax path P* = argmin_P max_i T_i(P) is found by evaluating
    candidate paths. For large graphs, candidate paths are generated
    heuristically; for small graphs, full enumeration can be used by
    passing `paths` explicitly.

    If return_diagnostics is True, returns (tau, diagnostics_dict) where
    diagnostics_dict contains candidate_count, T_min, T_max, tau, and
    candidate_puncts (punctuality of each candidate path against tau).
    """
    if paths is None:
        paths = generate_candidate_paths(W, network, origin, destination,
                                         max_paths=max_candidate_paths, seed=seed)

    if not paths:
        fallback = float(W.mean() * 3)
        if return_diagnostics:
            return fallback, {"candidate_count": 0, "T_min": 0.0, "T_max": 0.0,
                              "tau": fallback, "candidate_puncts": []}
        return fallback

    best_tmax = np.inf
    best_tmin = 0.0
    best_path = None

    for path in paths:
        x = network.path_to_x(path)
        path_times = W @ x
        max_time = path_times.max()
        min_time = path_times.min()

        if max_time < best_tmax:
            best_tmax = max_time
            best_tmin = min_time
            best_path = path

    tau = best_tmin + alpha * (best_tmax - best_tmin)

    if verbose:
        print(f"  [DEADLINE] candidates={len(paths)} T_min={best_tmin:.2f} "
              f"T_max={best_tmax:.2f} tau={tau:.2f}")

    if return_diagnostics:
        N = W.shape[0]
        candidate_puncts = []
        for path in paths:
            x = network.path_to_x(path)
            path_times = W @ x
            candidate_puncts.append(float(np.mean(path_times <= tau)))
        return tau, {
            "candidate_count": len(paths),
            "T_min": float(best_tmin),
            "T_max": float(best_tmax),
            "tau": float(tau),
            "candidate_puncts": candidate_puncts,
        }

    return tau


def generate_candidate_paths(W: np.ndarray, network: RoadNetwork,
                              origin: int, destination: int,
                              max_paths: int = 1000,
                              seed: int = 42) -> list[list[int]]:
    """Generate candidate paths for deadline computation.

    Uses 4 sources (priority order):
      1. Mean-weight shortest path
      2. Worst-case (max-weight) shortest path
      3. Per-sample shortest paths (up to 500 samples)
      4. K-shortest paths (Yen's algorithm on mean-weight graph)

    All sources are deduplicated and truncated to max_paths.
    """
    G = network.graph
    num_samples = W.shape[0]
    paths_set: set[tuple[int, ...]] = set()
    paths: list[list[int]] = []

    def _add_path(path: list[int]) -> bool:
        key = tuple(path)
        if key not in paths_set:
            paths_set.add(key)
            paths.append(path)
            return True
        return False

    def _shortest_path(weights: np.ndarray) -> list[int] | None:
        try:
            return nx.shortest_path(G, origin, destination,
                                    weight=lambda u, v, d: float(weights[network.edge_index((u, v))]))
        except (nx.NetworkXNoPath, KeyError):
            return None

    # Source 1: Mean-weight shortest path
    mean_weights = W.mean(axis=0)
    sp_mean = _shortest_path(mean_weights)
    if sp_mean:
        _add_path(sp_mean)

    # Source 2: Worst-case (max-weight) shortest path
    max_weights = W.max(axis=0)
    sp_worst = _shortest_path(max_weights)
    if sp_worst:
        _add_path(sp_worst)

    # Source 3: Per-sample shortest paths
    rng = np.random.default_rng(seed)
    per_sample_limit = min(num_samples, 500)
    sample_indices = rng.choice(num_samples, per_sample_limit, replace=False)
    for i in sample_indices:
        sp = _shortest_path(W[i, :])
        if sp:
            _add_path(sp)
            if len(paths) >= max_paths:
                return paths

    # Source 4: K-shortest paths (Yen's algorithm on mean-weight graph)
    try:
        for k_path in nx.shortest_simple_paths(G, origin, destination,
                                               weight=lambda u, v, d: float(mean_weights[network.edge_index((u, v))])):
            key = tuple(k_path)
            if key not in paths_set:
                paths_set.add(key)
                paths.append(k_path)
                if len(paths) >= max_paths:
                    break
    except (nx.NetworkXNoPath, nx.NetworkXError, KeyError):
        pass

    return paths


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


def generate_beijing_travel_times(network: RoadNetwork, num_samples: int,
                                  seed: int = 42) -> np.ndarray:
    """Generate attribute-driven travel times for Beijing road network.

    Each edge's lognormal distribution is determined by OSM attributes:
      - mean = edge["mean_time"] (minutes, derived from length/speed)
      - CV = Uniform(low, high) where range depends on road type

    Returns matrix W where W[i, j] = travel time of sample i on edge j.
    """
    rng = np.random.default_rng(seed)
    num_edges = network.num_edges
    W = np.zeros((num_samples, num_edges), dtype=np.float64)

    for j, (u, v) in enumerate(network.edges):
        edge_data = network.graph.edges[u, v]
        mean_time = float(edge_data.get("mean_time", 3.0))
        highway = edge_data.get("highway", "unclassified")
        cv_lo, cv_hi = get_highway_cv_range(highway)
        cv = rng.uniform(cv_lo, cv_hi)

        std_time = mean_time * cv
        sigma2 = np.log(1 + (std_time / mean_time) ** 2)
        mu = np.log(mean_time) - sigma2 / 2
        sigma = np.sqrt(sigma2)
        W[:, j] = rng.lognormal(mu, sigma, size=num_samples)

    return W
