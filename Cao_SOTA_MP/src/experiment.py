"""Experiment orchestration: run solvers, compare with ground truth."""

import gc
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .graph import RoadNetwork
from .generator import compute_deadline, generate_travel_times, random_od_pairs
from .ilp_solver import solve_ilp
from .milp_solver import solve_milp
from .dijkstra_solver import solve_dijkstra


def load_experiment_data(data_dir: str | Path) -> dict:
    """Load pre-generated experiment data from directory.

    Returns dict with keys: network, od_pairs, travel_times (list of W matrices), meta.
    """
    data_dir = Path(data_dir)
    network = RoadNetwork.load(data_dir / "network.npz")
    od_pairs = np.load(data_dir / "od_pairs.npy").tolist()
    od_pairs = [(int(o), int(d)) for o, d in od_pairs]

    tt_file = np.load(data_dir / "travel_times.npz")
    travel_times = []
    r = 0
    while f"repeat_{r:02d}" in tt_file:
        travel_times.append(tt_file[f"repeat_{r:02d}"])
        r += 1

    with open(data_dir / "meta.yaml") as f:
        meta = yaml.safe_load(f)

    return {
        "network": network,
        "od_pairs": od_pairs,
        "travel_times": travel_times,
        "meta": meta,
    }


def run_experiment(config: dict, data_dir: str | Path | None = None) -> pd.DataFrame:
    """Run the full comparison experiment.

    If data_dir is provided, loads pre-generated data from disk.
    Otherwise falls back to generating data inline (legacy mode).
    """
    exp_cfg = config.get("experiment", {})
    solver_cfg = config.get("solver", {})

    alphas = exp_cfg.get("alphas", [0.5, 0.6, 0.7, 0.8, 0.9])
    backend = solver_cfg.get("backend", "CBC")
    big_m = float(solver_cfg.get("big_m", 1e6))
    time_limit = int(solver_cfg.get("time_limit", 60))
    num_repeats = exp_cfg.get("num_repeats", 10)

    if data_dir:
        data = load_experiment_data(data_dir)
        network = data["network"]
        od_pairs = data["od_pairs"]
        travel_times = data["travel_times"]
        num_repeats = min(num_repeats, len(travel_times))
    else:
        data_cfg = config.get("data", {})
        net_cfg = config.get("network", {})
        from .generator import create_artificial_network
        network = create_artificial_network(
            net_cfg.get("num_nodes", 65),
            net_cfg.get("num_edges", 123),
            net_cfg.get("seed", 42),
        )
        num_samples = data_cfg.get("num_samples", 500)
        time_range = tuple(data_cfg.get("travel_time_range", [10, 100]))
        num_od_pairs = exp_cfg.get("num_od_pairs", 20)
        od_pairs = random_od_pairs(network, num_od_pairs, seed=net_cfg.get("seed", 42))
        travel_times = [
            generate_travel_times(network.num_edges, num_samples, time_range, seed=1000 + r)
            for r in range(num_repeats)
        ]

    print(f"  Network: {network.num_nodes} nodes, {network.num_edges} edges")
    print(f"  OD pairs: {len(od_pairs)}, Repeats: {num_repeats}, Alphas: {alphas}")

    results = []
    t_start = time.perf_counter()

    for repeat in range(num_repeats):
        W = travel_times[repeat]

        for oi, (o, d) in enumerate(od_pairs):
            for alpha in alphas:
                tau = compute_deadline(W, network, o, d, alpha)

                ilp_result = solve_ilp(network, W, o, d, tau, big_m, backend, time_limit)
                if ilp_result["status"] != "Optimal":
                    continue
                ilp_path = ilp_result["path_x"]
                ilp_prob = ilp_result["punctuality_prob"]

                milp_result = solve_milp(network, W, o, d, tau, backend, time_limit)
                milp_path = milp_result["path_x"] if milp_result["status"] == "Optimal" else None
                milp_prob = milp_result["punctuality_prob"] if milp_result["status"] == "Optimal" else None

                dij_result = solve_dijkstra(network, W, o, d, tau)
                dij_path = dij_result["path_x"]
                dij_prob = dij_result["punctuality_prob"]

                results.append({
                    "repeat": repeat, "od_idx": oi, "origin": o, "dest": d,
                    "alpha": alpha, "method": "ILP",
                    "punctuality_prob": ilp_prob,
                    "correct": True,
                    "solve_time": ilp_result["solve_time"],
                })
                results.append({
                    "repeat": repeat, "od_idx": oi, "origin": o, "dest": d,
                    "alpha": alpha, "method": "MILP",
                    "punctuality_prob": milp_prob,
                    "correct": _path_match(milp_path, ilp_path),
                    "solve_time": milp_result["solve_time"],
                })
                results.append({
                    "repeat": repeat, "od_idx": oi, "origin": o, "dest": d,
                    "alpha": alpha, "method": "Dijkstra",
                    "punctuality_prob": dij_prob,
                    "correct": _path_match(dij_path, ilp_path),
                    "solve_time": dij_result["solve_time"],
                })

        elapsed = time.perf_counter() - t_start
        print(f"  Repeat {repeat + 1}/{num_repeats} done ({elapsed:.1f}s elapsed)")
        gc.collect()

    return pd.DataFrame(results)


def _path_match(path_x, ref_path_x) -> bool | None:
    """Check if the method found the same path as ILP (by path vector identity)."""
    if path_x is None:
        return None
    return bool(np.array_equal(path_x, ref_path_x))
