"""Experiment runner facade for the public RSP SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd

from .config import RSPConfig
from .dataset import RSPDataset, RSPTimeDependentDataset
from .metrics import compute_path_stats, path_match, tie_aware_correct
from .result import RSPCaseResult, RSPResult
from .adapters.cao import compute_deadline, solve_dijkstra, solve_ilp, solve_milp
from .adapters.yang import solve_yang_otap_ilp


@dataclass
class RSPRunner:
    """In-memory SDK runner for single-case and batch RSP experiments."""

    dataset: RSPDataset | RSPTimeDependentDataset
    config: RSPConfig

    def run(self, progress: bool = True) -> RSPResult:
        """Run the configured experiment in memory and return an RSPResult."""
        num_repeats = self._configured_count(
            configured=self.config.num_repeats,
            available=self.dataset.num_repeats,
            name="num_repeats",
        )
        num_od_pairs = self._configured_count(
            configured=self.config.num_od_pairs,
            available=self.dataset.num_od_pairs,
            name="num_od_pairs",
        )

        rows: list[dict[str, Any]] = []
        total_jobs = num_repeats * num_od_pairs * len(self.config.alphas)
        job_idx = 0
        for repeat in range(num_repeats):
            for od_idx in range(num_od_pairs):
                for alpha in self.config.alphas:
                    job_idx += 1
                    case = self.solve_case(repeat=repeat, od_idx=od_idx, alpha=alpha)
                    rows.extend(self._case_to_rows(case))
                    if progress:
                        print(
                            f"[{job_idx}/{total_jobs}] "
                            f"repeat={repeat} od_idx={od_idx} alpha={alpha}"
                        )

        return RSPResult(
            df=pd.DataFrame(rows),
            config=self.config,
            dataset_meta=self.dataset.meta.copy(),
        )

    def solve_case(
        self,
        repeat: int = 0,
        od_idx: int | None = None,
        alpha: float | None = None,
        origin: int | None = None,
        destination: int | None = None,
    ) -> RSPCaseResult:
        """Solve one repeat/OD/alpha case through the public SDK boundary."""
        W = self._get_deadline_matrix(repeat)
        td = self._get_time_dependent_tensor(repeat)
        origin, destination, resolved_od_idx = self._resolve_od(
            od_idx=od_idx,
            origin=origin,
            destination=destination,
        )
        if alpha is None:
            alpha = self.config.alphas[0]
        alpha = float(alpha)
        if not 0.0 <= alpha <= 1.0:
            raise ValueError(f"alpha must be in [0, 1], got {alpha}")

        tau, deadline_diag = compute_deadline(
            W,
            self.dataset.network,
            origin,
            destination,
            alpha,
            max_candidate_paths=self.config.max_candidate_paths,
            mode=self.config.deadline_mode,
            enumeration_cutoff=self.config.deadline_enumeration_cutoff,
            seed=self.config.random_seed + repeat * 100 + (resolved_od_idx or 0),
            return_diagnostics=True,
        )

        raw_results: dict[str, dict[str, Any]] = {}
        if "ILP" in self.config.methods:
            raw_results["ILP"] = solve_ilp(
                self.dataset.network,
                W,
                origin,
                destination,
                tau,
                self.config.big_m,
                self.config.solver_backend,
                self.config.time_limit,
            )
        if "MILP" in self.config.methods:
            raw_results["MILP"] = solve_milp(
                self.dataset.network,
                W,
                origin,
                destination,
                tau,
                self.config.solver_backend,
                self.config.time_limit,
            )
        if "Dijkstra" in self.config.methods:
            raw_results["Dijkstra"] = solve_dijkstra(
                self.dataset.network,
                W,
                origin,
                destination,
                tau,
            )
        if "Yang_OTAP_ILP" in self.config.methods:
            if td is None:
                raise ValueError(
                    "Yang_OTAP_ILP requires RSPTimeDependentDataset. "
                    "Use RSPTimeDependentDataset.from_arrays(), from_cao_dataset(), "
                    "or from_networkx()."
                )
            raw_results["Yang_OTAP_ILP"] = solve_yang_otap_ilp(
                network=self.dataset.network,
                travel_times=td,
                origin=origin,
                destination=destination,
                tau=tau,
                time_step=self.dataset.time_step,
                sample_probabilities=self.dataset.sample_probabilities,
                big_m=self.config.big_m,
                solver_name=self.config.solver_backend,
                time_limit=self.config.time_limit,
            )

        metrics = self._build_case_metrics(
            raw_results=raw_results,
            W=W,
            tau=tau,
            repeat=repeat,
            od_idx=resolved_od_idx,
            origin=origin,
            destination=destination,
            alpha=alpha,
            deadline_diag=deadline_diag,
        )

        return RSPCaseResult(
            tau=float(tau),
            ilp=raw_results.get("ILP"),
            milp=raw_results.get("MILP"),
            dijkstra=raw_results.get("Dijkstra"),
            metrics=metrics,
        )

    def _get_repeat_matrix(self, repeat: int) -> np.ndarray:
        if repeat < 0 or repeat >= self.dataset.num_repeats:
            raise IndexError(
                f"repeat index {repeat} out of range for {self.dataset.num_repeats} repeats"
            )
        return self.dataset.travel_times[repeat]

    def _get_deadline_matrix(self, repeat: int) -> np.ndarray:
        """Return Cao-style samples used for deadline computation and static methods."""
        if isinstance(self.dataset, RSPTimeDependentDataset):
            return self.dataset.deadline_matrix(repeat)
        return self._get_repeat_matrix(repeat)

    def _get_time_dependent_tensor(self, repeat: int) -> np.ndarray | None:
        """Return the TD tensor for Yang methods, or None for static datasets."""
        if not isinstance(self.dataset, RSPTimeDependentDataset):
            return None
        if repeat < 0 or repeat >= self.dataset.num_repeats:
            raise IndexError(
                f"repeat index {repeat} out of range for {self.dataset.num_repeats} repeats"
            )
        return self.dataset.travel_times[repeat]

    def _configured_count(self, configured: int | None, available: int, name: str) -> int:
        if configured is None:
            return available
        if configured <= 0:
            raise ValueError(f"{name} must be positive")
        if configured > available:
            raise ValueError(f"{name}={configured} exceeds available count {available}")
        return configured

    def _resolve_od(
        self,
        od_idx: int | None,
        origin: int | None,
        destination: int | None,
    ) -> tuple[int, int, int | None]:
        if od_idx is not None:
            if od_idx < 0 or od_idx >= self.dataset.num_od_pairs:
                raise IndexError(
                    f"od_idx {od_idx} out of range for {self.dataset.num_od_pairs} OD pairs"
                )
            resolved_origin, resolved_destination = self.dataset.od_pairs[od_idx]
            if origin is not None and int(origin) != resolved_origin:
                raise ValueError("origin does not match od_idx")
            if destination is not None and int(destination) != resolved_destination:
                raise ValueError("destination does not match od_idx")
            return resolved_origin, resolved_destination, od_idx

        if origin is None or destination is None:
            raise ValueError("Provide either od_idx or both origin and destination")
        resolved_origin = int(origin)
        resolved_destination = int(destination)
        node_set = set(self.dataset.network.nodes)
        if resolved_origin not in node_set or resolved_destination not in node_set:
            raise ValueError(
                "origin and destination must both be present in the dataset network"
            )
        if resolved_origin == resolved_destination:
            raise ValueError("origin and destination must be different")
        if not nx.has_path(
            self.dataset.network.graph,
            resolved_origin,
            resolved_destination,
        ):
            raise ValueError(
                f"No path from origin {resolved_origin} to destination {resolved_destination}"
            )
        return resolved_origin, resolved_destination, None

    def _build_case_metrics(
        self,
        raw_results: dict[str, dict[str, Any]],
        W: np.ndarray,
        tau: float,
        repeat: int,
        od_idx: int | None,
        origin: int,
        destination: int,
        alpha: float,
        deadline_diag: dict[str, Any],
    ) -> dict[str, Any]:
        ilp_result = raw_results.get("ILP")
        reference_available = (
            ilp_result is not None and ilp_result.get("status") == "Optimal"
        )
        reference_path = ilp_result.get("path_x") if reference_available else None
        reference_prob = (
            ilp_result.get("punctuality_prob") if reference_available else None
        )

        methods: dict[str, dict[str, Any]] = {}
        for method, result in raw_results.items():
            method_path = result.get("path_x") if result.get("status") == "Optimal" else None
            method_prob = result.get("punctuality_prob") if result.get("status") == "Optimal" else None
            stats = self._method_path_stats(method, result, W, method_path, tau)
            if reference_available and method_prob is not None:
                objective_gap = float(reference_prob - method_prob)
                tie_ok = tie_aware_correct(method_prob, reference_prob, W.shape[0])
                correct = path_match(method_path, reference_path)
            else:
                objective_gap = None
                tie_ok = None
                correct = None

            methods[method] = {
                "punctuality_prob": method_prob,
                "status": result.get("status"),
                "solve_time": result.get("solve_time"),
                "lateness_count": result.get("lateness_count"),
                "on_time_count": result.get("on_time_count"),
                "path_edges": result.get("path_edges"),
                "sample_travel_times": result.get("sample_travel_times"),
                "arrival_time_indices": result.get("arrival_time_indices"),
                "time_step": result.get("time_step"),
                "conclusion": result.get("conclusion"),
                "correct": correct,
                "objective_gap": objective_gap,
                "tie_aware_correct": tie_ok,
                **stats,
            }

        return {
            "repeat": repeat,
            "od_idx": od_idx,
            "origin": origin,
            "destination": destination,
            "alpha": alpha,
            "tau": float(tau),
            "deadline": deadline_diag,
            "reference_available": reference_available,
            "reference_status": ilp_result.get("status") if ilp_result else None,
            "methods": methods,
        }

    def _method_path_stats(
        self,
        method: str,
        result: dict[str, Any],
        W: np.ndarray,
        method_path: np.ndarray | None,
        tau: float,
    ) -> dict[str, Any]:
        if method == "Yang_OTAP_ILP" and result.get("sample_travel_times") is not None:
            path_times = np.asarray(result["sample_travel_times"], dtype=np.float64)
            delays = np.maximum(0, path_times - float(tau))
            path_x = result.get("path_x")
            return {
                "late_count": result.get("lateness_count"),
                "delay_sum": float(np.sum(delays)),
                "max_delay": float(np.max(delays)),
                "path_length": int(np.sum(path_x)) if path_x is not None else None,
                "mean_time": float(np.mean(path_times)),
            }
        return compute_path_stats(W, method_path, tau)

    def _case_to_rows(self, case: RSPCaseResult) -> list[dict[str, Any]]:
        rows = []
        case_meta = case.metrics
        for method in self.config.methods:
            method_metrics = case_meta["methods"].get(method)
            if method_metrics is None:
                continue
            rows.append(
                {
                    "repeat": case_meta["repeat"],
                    "od_idx": case_meta["od_idx"],
                    "origin": case_meta["origin"],
                    "dest": case_meta["destination"],
                    "destination": case_meta["destination"],
                    "alpha": case_meta["alpha"],
                    "tau": case_meta["tau"],
                    "method": method,
                    "punctuality_prob": method_metrics["punctuality_prob"],
                    "correct": method_metrics["correct"],
                    "objective_gap": method_metrics["objective_gap"],
                    "tie_aware_correct": method_metrics["tie_aware_correct"],
                    "late_count": method_metrics["late_count"],
                    "lateness_count": method_metrics["lateness_count"],
                    "on_time_count": method_metrics.get("on_time_count"),
                    "delay_sum": method_metrics["delay_sum"],
                    "max_delay": method_metrics["max_delay"],
                    "path_length": method_metrics["path_length"],
                    "mean_time": method_metrics["mean_time"],
                    "path_edges": method_metrics.get("path_edges"),
                    "sample_travel_times": method_metrics.get("sample_travel_times"),
                    "arrival_time_indices": method_metrics.get("arrival_time_indices"),
                    "time_step": method_metrics.get("time_step"),
                    "conclusion": method_metrics.get("conclusion"),
                    "status": method_metrics["status"],
                    "reference_available": case_meta["reference_available"],
                    "reference_status": case_meta["reference_status"],
                    "deadline_mode": self.config.deadline_mode,
                    "solve_time": method_metrics["solve_time"],
                }
            )
        return rows
