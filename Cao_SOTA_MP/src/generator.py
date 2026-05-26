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
                     mode: str = "heuristic",
                     enumeration_cutoff: int = 15,
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
        if mode == "exact":
            paths = network.enumerate_paths(
                origin,
                destination,
                cutoff=enumeration_cutoff,
            )
        elif mode == "heuristic":
            paths = generate_candidate_paths(
                W,
                network,
                origin,
                destination,
                max_paths=max_candidate_paths,
                seed=seed,
            )
        else:
            raise ValueError(f"Unsupported deadline mode: {mode}")

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
              f"T_max={best_tmax:.2f} tau={tau:.2f} mode={mode}")

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
            "mode": mode,
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


def assign_conflict_edge_types(network: RoadNetwork, seed: int = 42) -> None:
    """Assign dual edge types (fast_risky / slow_stable) to a network in-place.

    Must be called once before ``generate_conflict_travel_times`` so edge types
    are consistent across repeats and survive serialization.
    """
    rng = np.random.default_rng(seed)
    num_edges = network.num_edges
    edge_types = ["fast_risky"] * (num_edges // 2) + ["slow_stable"] * (num_edges - num_edges // 2)
    rng.shuffle(edge_types)
    for j, (u, v) in enumerate(network.edges):
        network.graph.edges[u, v]["edge_type"] = edge_types[j]


def generate_conflict_travel_times(network: RoadNetwork, num_samples: int,
                                    seed: int = 42) -> np.ndarray:
    """Generate travel times with dual edge types to induce path conflicts.

    Edge types must already be assigned on the graph via
    ``assign_conflict_edge_types`` before calling this function.

    Returns matrix W where W[i, j] = travel time of sample i on edge j.
    """
    rng = np.random.default_rng(seed)
    num_edges = network.num_edges
    W = np.zeros((num_samples, num_edges), dtype=np.float64)

    for j, (u, v) in enumerate(network.edges):
        etype = network.graph.edges[u, v].get("edge_type", "slow_stable")

        if etype == "fast_risky":
            mean_time = rng.uniform(10.0, 50.0)
            cv = rng.uniform(0.8, 1.4)
        else:  # slow_stable
            mean_time = rng.uniform(40.0, 90.0)
            cv = rng.uniform(0.2, 0.6)

        std_time = mean_time * cv
        sigma2 = np.log(1 + (std_time / mean_time) ** 2)
        mu = np.log(mean_time) - sigma2 / 2
        sigma = np.sqrt(sigma2)
        W[:, j] = rng.lognormal(mu, sigma, size=num_samples)

    return W


# ── Beijing Multi-Level Conflict Variance ──────────────────────────────

BEIJING_CONFLICT_TIERS = {
    "express":   {"highways": {"trunk", "trunk_link"},             "volatile_pct": 0.50},
    "arterial":  {"highways": {"primary", "primary_link"},          "volatile_pct": 0.40},
    "collector": {"highways": {"secondary_link"},                   "volatile_pct": 0.25},
    "local":     {"highways": {"secondary"},                        "volatile_pct": 0.15},
}

BEIJING_CONFLICT_CV = {
    "express_stable":      (0.6, 1.0),
    "express_volatile":    (1.4, 2.2),
    "arterial_stable":     (0.4, 0.7),
    "arterial_volatile":   (1.0, 1.8),
    "collector_stable":    (0.3, 0.5),
    "collector_volatile":  (0.7, 1.2),
    "local_stable":        (0.2, 0.4),
    "local_volatile":      (0.5, 0.9),
}


def _get_beijing_tier(highway: str) -> str:
    """Map OSM highway type to Beijing conflict tier."""
    for tier_name, tier_info in BEIJING_CONFLICT_TIERS.items():
        if highway in tier_info["highways"]:
            return tier_name
    return "local"


def assign_beijing_conflict_edge_types(network: RoadNetwork, seed: int = 42) -> None:
    """Assign multi-level conflict edge types to Beijing network in-place.

    Each edge gets a tier from its highway type and a variant (stable/volatile)
    based on the tier's volatile probability. Must be called once before
    ``generate_beijing_conflict_travel_times``.
    """
    rng = np.random.default_rng(seed)
    for u, v in network.edges:
        highway = network.graph.edges[u, v].get("highway", "secondary")
        tier = _get_beijing_tier(highway)
        volatile_pct = BEIJING_CONFLICT_TIERS[tier]["volatile_pct"]
        variant = "volatile" if rng.random() < volatile_pct else "stable"
        network.graph.edges[u, v]["edge_type"] = f"{tier}_{variant}"


def generate_beijing_conflict_travel_times(network: RoadNetwork, num_samples: int,
                                            seed: int = 42) -> np.ndarray:
    """Generate travel times for Beijing network with multi-level conflict variance.

    Edge types must already be assigned via ``assign_beijing_conflict_edge_types``.
    Each edge uses its OSM-derived mean_time with CV from BEIJING_CONFLICT_CV.
    """
    rng = np.random.default_rng(seed)
    num_edges = network.num_edges
    W = np.zeros((num_samples, num_edges), dtype=np.float64)

    for j, (u, v) in enumerate(network.edges):
        edge_data = network.graph.edges[u, v]
        mean_time = float(edge_data.get("mean_time", 3.0))
        etype = edge_data.get("edge_type", "local_stable")
        cv_lo, cv_hi = BEIJING_CONFLICT_CV.get(etype, (0.3, 0.7))
        cv = rng.uniform(cv_lo, cv_hi)

        std_time = mean_time * cv
        sigma2 = np.log(1 + (std_time / mean_time) ** 2)
        mu = np.log(mean_time) - sigma2 / 2
        sigma = np.sqrt(sigma2)
        W[:, j] = rng.lognormal(mu, sigma, size=num_samples)

    return W
