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


def run_experiment(config: dict, data_dir: str | Path | None = None,
                   return_aux: bool = False) -> pd.DataFrame | tuple[pd.DataFrame, dict]:
    """Run the full comparison experiment.

    If data_dir is provided, loads pre-generated data from disk.
    Otherwise falls back to generating data inline (legacy mode).
    """
    exp_cfg = config.get("experiment", {})
    solver_cfg = config.get("solver", {})
    cp_cfg = config.get("candidate_paths", {})
    deadline_cfg = config.get("deadline", {})

    alphas = exp_cfg.get("alphas", [0.5, 0.6, 0.7, 0.8, 0.9])
    backend = solver_cfg.get("backend", "CBC")
    big_m = float(solver_cfg.get("big_m", 1e6))
    time_limit = int(solver_cfg.get("time_limit", 60))
    num_repeats = exp_cfg.get("num_repeats", 10)
    max_candidate_paths = cp_cfg.get("max_paths", 1000)
    deadline_mode = deadline_cfg.get("mode", "heuristic")
    deadline_enumeration_cutoff = int(deadline_cfg.get("enumeration_cutoff", 15))
    base_seed = config.get("network", {}).get("seed", 42)

    if data_dir:
        data = load_experiment_data(data_dir)
        network = data["network"]
        od_pairs = data["od_pairs"]
        travel_times = data["travel_times"]
        num_repeats = min(num_repeats, len(travel_times))
        num_od = exp_cfg.get("num_od_pairs", len(od_pairs))
        od_pairs = od_pairs[:num_od]
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
    print(f"  Candidate paths: max {max_candidate_paths}, deadline mode={deadline_mode}")

    results = []
    deadline_diag_by_alpha: dict[float, list[dict]] = {a: [] for a in alphas}
    t_start = time.perf_counter()
    total_jobs = num_repeats * len(od_pairs) * len(alphas)
    job_idx = 0

    for repeat in range(num_repeats):
        W = travel_times[repeat]
        N = W.shape[0]
        t_repeat = time.perf_counter()

        for oi, (o, d) in enumerate(od_pairs):
            for ai, alpha in enumerate(alphas):
                job_idx += 1
                tau, tau_diag = compute_deadline(
                    W, network, o, d, alpha,
                    max_candidate_paths=max_candidate_paths,
                    mode=deadline_mode,
                    enumeration_cutoff=deadline_enumeration_cutoff,
                    seed=base_seed + repeat * 100 + oi,
                    return_diagnostics=True,
                )
                deadline_diag_by_alpha[alpha].append(tau_diag)

                t0 = time.perf_counter()
                ilp_result = solve_ilp(network, W, o, d, tau, big_m, backend, time_limit)
                t_ilp = time.perf_counter() - t0
                ilp_status = ilp_result["status"]
                reference_available = ilp_status == "Optimal"
                ilp_path = ilp_result["path_x"] if reference_available else None
                ilp_prob = ilp_result["punctuality_prob"] if reference_available else np.nan
                ilp_stats = _compute_path_stats(W, ilp_path, tau)

                t0 = time.perf_counter()
                milp_result = solve_milp(network, W, o, d, tau, backend, time_limit)
                t_milp = time.perf_counter() - t0
                milp_path = milp_result["path_x"] if milp_result["status"] == "Optimal" else None
                milp_prob = milp_result["punctuality_prob"] if milp_result["status"] == "Optimal" else np.nan

                t0 = time.perf_counter()
                dij_result = solve_dijkstra(network, W, o, d, tau)
                t_dij = time.perf_counter() - t0
                dij_path = dij_result["path_x"]
                dij_prob = dij_result["punctuality_prob"]

                # Shared fields for all 3 methods
                if reference_available:
                    ilp_gap = 0.0
                    ilp_tie_ok = True
                    gap_milp = ilp_prob - milp_prob if not np.isnan(milp_prob) else np.nan
                    milp_tie_ok = abs(gap_milp) <= 1.0 / N if not np.isnan(gap_milp) else np.nan
                    gap_dij = ilp_prob - dij_prob if not np.isnan(dij_prob) else np.nan
                    dij_tie_ok = abs(gap_dij) <= 1.0 / N if not np.isnan(gap_dij) else np.nan
                else:
                    ilp_gap = np.nan
                    ilp_tie_ok = np.nan
                    gap_milp = np.nan
                    milp_tie_ok = np.nan
                    gap_dij = np.nan
                    dij_tie_ok = np.nan

                milp_stats = _compute_path_stats(W, milp_path, tau)
                dij_stats = _compute_path_stats(W, dij_path, tau)

                results.append({
                    "repeat": repeat, "od_idx": oi, "origin": o, "dest": d,
                    "alpha": alpha, "method": "ILP",
                    "punctuality_prob": ilp_prob,
                    "correct": True if reference_available else np.nan,
                    "objective_gap": ilp_gap,
                    "tie_aware_correct": ilp_tie_ok,
                    "late_count": ilp_stats["late_count"],
                    "delay_sum": ilp_stats["delay_sum"],
                    "max_delay": ilp_stats["max_delay"],
                    "path_length": ilp_stats["path_length"],
                    "mean_time": ilp_stats["mean_time"],
                    "status": ilp_status,
                    "reference_available": reference_available,
                    "reference_status": ilp_status,
                    "deadline_mode": deadline_mode,
                    "solve_time": ilp_result["solve_time"],
                })
                results.append({
                    "repeat": repeat, "od_idx": oi, "origin": o, "dest": d,
                    "alpha": alpha, "method": "MILP",
                    "punctuality_prob": milp_prob,
                    "correct": _path_match(milp_path, ilp_path) if reference_available else np.nan,
                    "objective_gap": gap_milp,
                    "tie_aware_correct": milp_tie_ok,
                    "late_count": milp_stats["late_count"],
                    "delay_sum": milp_stats["delay_sum"],
                    "max_delay": milp_stats["max_delay"],
                    "path_length": milp_stats["path_length"],
                    "mean_time": milp_stats["mean_time"],
                    "status": milp_result["status"],
                    "reference_available": reference_available,
                    "reference_status": ilp_status,
                    "deadline_mode": deadline_mode,
                    "solve_time": milp_result["solve_time"],
                })
                results.append({
                    "repeat": repeat, "od_idx": oi, "origin": o, "dest": d,
                    "alpha": alpha, "method": "Dijkstra",
                    "punctuality_prob": dij_prob,
                    "correct": _path_match(dij_path, ilp_path) if reference_available else np.nan,
                    "objective_gap": gap_dij,
                    "tie_aware_correct": dij_tie_ok,
                    "late_count": dij_stats["late_count"],
                    "delay_sum": dij_stats["delay_sum"],
                    "max_delay": dij_stats["max_delay"],
                    "path_length": dij_stats["path_length"],
                    "mean_time": dij_stats["mean_time"],
                    "status": dij_result["status"],
                    "reference_available": reference_available,
                    "reference_status": ilp_status,
                    "deadline_mode": deadline_mode,
                    "solve_time": dij_result["solve_time"],
                })

                # Per-job progress
                elapsed = time.perf_counter() - t_start
                avg_per_job = elapsed / job_idx
                eta = avg_per_job * (total_jobs - job_idx)
                eta_str = f"{eta/60:.0f}m{eta%60:.0f}s" if eta < 3600 else f"{eta/3600:.1f}h"
                ref_note = "" if reference_available else " ref=missing"
                print(f"  [{job_idx}/{total_jobs}] R{repeat+1} OD{oi+1} α={alpha} | "
                      f"ILP={t_ilp:.1f}s ({ilp_status}) MILP={t_milp:.1f}s Dij={t_dij:.3f}s{ref_note} | "
                      f"elapsed={elapsed/60:.1f}m ETA={eta_str}")

        t_repeat_elapsed = time.perf_counter() - t_repeat
        total_elapsed = time.perf_counter() - t_start
        print(f"  Repeat {repeat + 1}/{num_repeats} done ({t_repeat_elapsed/60:.1f}m, total {total_elapsed/60:.1f}m)")
        gc.collect()

    df = pd.DataFrame(results)

    # Deadline diagnostics
    print("\n=== Deadline Diagnostics ===")
    for alpha in alphas:
        diags = deadline_diag_by_alpha[alpha]
        ilp_rows = df[(df["method"] == "ILP") & (df["alpha"] == alpha)]
        ilp_puncts = ilp_rows["punctuality_prob"].dropna()
        all_cand_puncts = []
        for d in diags:
            all_cand_puncts.extend(d.get("candidate_puncts", []))
        cand_mean = np.mean(all_cand_puncts) if all_cand_puncts else float("nan")

        print(f"  α={alpha}: tau mean={np.mean([d['tau'] for d in diags]):.1f} "
              f"ILP_punct median={ilp_puncts.median():.3f} mean={ilp_puncts.mean():.3f} "
              f"min={ilp_puncts.min():.3f} max={ilp_puncts.max():.3f} | "
              f"cand_punct mean={cand_mean:.3f} n_candidates={len(diags)}")
        if alpha >= 0.9 and cand_mean > 0.99:
            print(f"    ⚠ deadline too loose at α={alpha}: candidate path punctuality mean > 0.99, low discrimination")

    if return_aux:
        return df, {
            "deadline_diag_by_alpha": deadline_diag_by_alpha,
            "alphas": alphas,
            "deadline_mode": deadline_mode,
        }
    return df


def _path_match(path_x, ref_path_x) -> bool | None:
    """Check if the method found the same path as ILP (by path vector identity)."""
    if path_x is None:
        return None
    return bool(np.array_equal(path_x, ref_path_x))


def _compute_path_stats(W: np.ndarray, path_x: np.ndarray | None,
                         tau: float) -> dict:
    """Compute per-instance diagnostic statistics for a path.

    Returns dict with late_count, delay_sum, max_delay, path_length, mean_time.
    All values are None if path_x is None.
    """
    if path_x is None:
        return {"late_count": None, "delay_sum": None, "max_delay": None,
                "path_length": None, "mean_time": None}
    path_times = W @ path_x
    delays = np.maximum(0, path_times - tau)
    return {
        "late_count": int(np.sum(path_times > tau)),
        "delay_sum": float(np.sum(delays)),
        "max_delay": float(np.max(delays)),
        "path_length": int(np.sum(path_x)),
        "mean_time": float(np.mean(path_times)),
    }


def _save_worst_cases(df: pd.DataFrame, output_dir: str | Path) -> None:
    """Save rows where MILP punctuality < Dijkstra punctuality to worst_cases.csv."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    milp_df = df[df["method"] == "MILP"].set_index(
        ["repeat", "od_idx", "origin", "dest", "alpha"]
    )
    dij_df = df[df["method"] == "Dijkstra"].set_index(
        ["repeat", "od_idx", "origin", "dest", "alpha"]
    )

    common_idx = milp_df.index.intersection(dij_df.index)
    milp_p = milp_df.loc[common_idx, "punctuality_prob"]
    dij_p = dij_df.loc[common_idx, "punctuality_prob"]

    mask = milp_p < dij_p
    if not mask.any():
        print("  No worst cases found (MILP >= Dijkstra for all instances)")
        return

    worst_idx = milp_p[mask].index
    worst_rows = []
    cols = ["method", "punctuality_prob", "objective_gap", "tie_aware_correct",
            "path_length", "mean_time", "late_count", "delay_sum", "max_delay",
            "solve_time", "correct"]

    for idx in worst_idx:
        for method in ["ILP", "MILP", "Dijkstra"]:
            row = df[
                (df["method"] == method)
                & (df["repeat"] == idx[0])
                & (df["od_idx"] == idx[1])
                & (df["alpha"] == idx[4])
            ]
            if len(row) > 0:
                r = row.iloc[0]
                worst_rows.append({c: r.get(c) for c in cols + ["repeat", "od_idx", "origin", "dest", "alpha"]} |
                                  {"method": method})

    worst_df = pd.DataFrame(worst_rows)
    path = output_dir / "worst_cases.csv"
    worst_df.to_csv(path, index=False)
    print(f"  Saved {len(worst_idx)} worst cases to {path}")
