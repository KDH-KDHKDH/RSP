"""Exact Yang OTAP ILP solver on sample-based time-dependent travel times."""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any

import numpy as np
import pulp

from Cao_SOTA_MP.src.graph import RoadNetwork
from Cao_SOTA_MP.src.ilp_solver import _get_solver, _new_variable


@dataclass(frozen=True)
class TimeSpaceArc:
    """A directed arc in one sample's time-expanded network."""

    tail: tuple[int, int] | str
    head: tuple[int, int] | str
    edge_idx: int | None
    elapsed_time: float
    arrival_index: int | None


def duration_to_time_steps(duration: float, time_step: float) -> int:
    """Convert a positive travel duration to at least one discrete time step."""
    duration = float(duration)
    time_step = float(time_step)
    if duration <= 0:
        raise ValueError("duration must be positive")
    if time_step <= 0:
        raise ValueError("time_step must be positive")
    return max(1, int(math.ceil(duration / time_step - 1e-12)))


def solve_yang_otap_ilp(
    network: RoadNetwork,
    travel_times: np.ndarray,
    origin: int,
    destination: int,
    tau: float,
    time_step: float = 1.0,
    sample_probabilities: np.ndarray | None = None,
    big_m: float = 1_000_000,
    solver_name: str = "CBC",
    time_limit: int = 60,
) -> dict[str, Any]:
    """Solve Yang OTAP as a single-stage ILP over time-expanded samples.

    Args:
        network: Physical road network.
        travel_times: Tensor shaped (samples, time_steps, edges).
        origin: Origin node.
        destination: Destination node.
        tau: On-time threshold in the same units as time_step/travel_times.
        time_step: Discrete time-step length.
        sample_probabilities: Optional sample probabilities. Equal weights if None.
        big_m: Big-M cap for per-sample late indicator constraints.
        solver_name: PuLP backend name.
        time_limit: Solver time limit in seconds.

    Returns:
        Dict aligned with Cao solver outputs plus Yang diagnostics.
    """
    td = _validate_inputs(
        network=network,
        travel_times=travel_times,
        origin=origin,
        destination=destination,
        tau=tau,
        time_step=time_step,
    )
    num_samples, num_time_steps, num_edges = td.shape
    probabilities = _normalize_probabilities(sample_probabilities, num_samples)

    horizon_index = num_time_steps
    horizon_time = horizon_index * float(time_step)
    arcs_by_sample = [
        _build_time_space_arcs(
            network=network,
            sample_times=td[k],
            destination=destination,
            time_step=time_step,
            horizon_index=horizon_index,
        )
        for k in range(num_samples)
    ]

    if any(not arcs for arcs in arcs_by_sample):
        return _failure_result("InfeasibleTimeHorizon", tau, time_step)

    prob = pulp.LpProblem("Yang_OTAP_ILP", pulp.LpMinimize)

    x = [_new_variable(f"x_{j}", cat="Binary") for j in range(num_edges)]
    z = [_new_variable(f"late_{k}", cat="Binary") for k in range(num_samples)]
    y: list[list[pulp.LpVariable]] = []
    for k, arcs in enumerate(arcs_by_sample):
        y.append([_new_variable(f"y_{k}_{a}", cat="Binary") for a in range(len(arcs))])

    prob += pulp.lpSum(float(probabilities[k]) * z[k] for k in range(num_samples))

    # Physical path conservation.
    incidence = network.incidence_matrix()
    od = network.od_vector(origin, destination)
    for v in range(network.num_nodes):
        prob += (
            pulp.lpSum(incidence[v, j] * x[j] for j in range(num_edges)) == od[v],
            f"physical_flow_{v}",
        )

    sink = "sink"
    source = (origin, 0)
    for k, arcs in enumerate(arcs_by_sample):
        variables = y[k]
        nodes = _time_space_nodes(network, horizon_index, sink)

        for node in nodes:
            supply = 1.0 if node == source else -1.0 if node == sink else 0.0
            outgoing = [
                variables[a_idx]
                for a_idx, arc in enumerate(arcs)
                if arc.tail == node
            ]
            incoming = [
                variables[a_idx]
                for a_idx, arc in enumerate(arcs)
                if arc.head == node
            ]
            prob += (
                pulp.lpSum(outgoing) - pulp.lpSum(incoming) == supply,
                f"time_flow_{k}_{_node_name(node)}",
            )

        for edge_idx in range(num_edges):
            edge_arc_vars = [
                variables[a_idx]
                for a_idx, arc in enumerate(arcs)
                if arc.edge_idx == edge_idx
            ]
            prob += (
                pulp.lpSum(edge_arc_vars) == x[edge_idx],
                f"link_{k}_{edge_idx}",
            )

        sample_time = pulp.lpSum(
            arc.elapsed_time * variables[a_idx]
            for a_idx, arc in enumerate(arcs)
        )
        sample_max_time = _max_reachable_elapsed_time(
            arcs=arcs,
            source=source,
            sink=sink,
        )
        Mi = min(float(big_m), max(1.0, sample_max_time - float(tau)))
        prob += (sample_time - Mi * z[k] <= float(tau), f"late_indicator_{k}")

    solver = _get_solver(solver_name, time_limit)
    t0 = time.perf_counter()
    try:
        prob.solve(solver)
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        result = _failure_result(f"SolverError: {exc}", tau, time_step)
        result["solve_time"] = elapsed
        return result
    elapsed = time.perf_counter() - t0

    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        result = _failure_result(status, tau, time_step)
        result["solve_time"] = elapsed
        return result

    path_x = np.array([float(var.varValue or 0.0) for var in x], dtype=np.float64)
    path_edges = [
        tuple(network.edges[j])
        for j, value in enumerate(path_x)
        if value > 0.5
    ]
    sample_travel_times = np.zeros(num_samples, dtype=np.float64)
    arrival_time_indices = np.zeros(num_samples, dtype=np.int32)

    for k, arcs in enumerate(arcs_by_sample):
        selected = [
            arc
            for a_idx, arc in enumerate(arcs)
            if float(y[k][a_idx].varValue or 0.0) > 0.5
        ]
        sample_travel_times[k] = float(sum(arc.elapsed_time for arc in selected))
        dummy_arrivals = [
            arc.arrival_index
            for arc in selected
            if arc.edge_idx is None and arc.arrival_index is not None
        ]
        arrival_time_indices[k] = int(dummy_arrivals[0]) if dummy_arrivals else int(
            round(sample_travel_times[k] / float(time_step))
        )

    on_time_mask = sample_travel_times <= float(tau) + 1e-9
    on_time_count = int(np.sum(on_time_mask))
    lateness_count = int(num_samples - on_time_count)
    punctuality_prob = float(np.sum(probabilities[on_time_mask]))

    return {
        "path_x": path_x,
        "path_edges": path_edges,
        "lateness_count": lateness_count,
        "on_time_count": on_time_count,
        "punctuality_prob": punctuality_prob,
        "sample_travel_times": sample_travel_times,
        "arrival_time_indices": arrival_time_indices,
        "threshold": float(tau),
        "time_step": float(time_step),
        "status": status,
        "solve_time": elapsed,
        "conclusion": _build_conclusion(
            path_edges=path_edges,
            punctuality_prob=punctuality_prob,
            tau=float(tau),
            on_time_count=on_time_count,
            num_samples=num_samples,
        ),
    }


def _validate_inputs(
    network: RoadNetwork,
    travel_times: np.ndarray,
    origin: int,
    destination: int,
    tau: float,
    time_step: float,
) -> np.ndarray:
    if not isinstance(network, RoadNetwork):
        raise TypeError("network must be a RoadNetwork")
    td = np.asarray(travel_times, dtype=np.float64)
    if td.ndim != 3:
        raise ValueError(f"travel_times must be 3D (samples, time_steps, edges), got shape {td.shape}")
    if td.shape[2] != network.num_edges:
        raise ValueError(
            f"travel_times has {td.shape[2]} edge columns, expected {network.num_edges}"
        )
    if td.shape[0] <= 0 or td.shape[1] <= 0:
        raise ValueError("travel_times must have positive sample and time dimensions")
    if np.any(td <= 0):
        raise ValueError("travel_times must contain positive values")
    if float(time_step) <= 0:
        raise ValueError("time_step must be positive")
    if float(tau) < 0:
        raise ValueError("tau must be non-negative")
    node_set = set(network.nodes)
    if origin not in node_set or destination not in node_set:
        raise ValueError("origin and destination must both be present in network")
    if origin == destination:
        raise ValueError("origin and destination must be different")
    return td


def _normalize_probabilities(
    sample_probabilities: np.ndarray | None,
    num_samples: int,
) -> np.ndarray:
    if sample_probabilities is None:
        return np.full(num_samples, 1.0 / num_samples, dtype=np.float64)
    probabilities = np.asarray(sample_probabilities, dtype=np.float64)
    if probabilities.ndim != 1:
        raise ValueError("sample_probabilities must be a 1D array")
    if probabilities.shape[0] != num_samples:
        raise ValueError("sample_probabilities length must match num_samples")
    if np.any(probabilities < 0):
        raise ValueError("sample_probabilities must be non-negative")
    if not np.isclose(float(np.sum(probabilities)), 1.0):
        raise ValueError("sample_probabilities must sum to 1")
    return probabilities


def _build_time_space_arcs(
    network: RoadNetwork,
    sample_times: np.ndarray,
    destination: int,
    time_step: float,
    horizon_index: int,
) -> list[TimeSpaceArc]:
    arcs: list[TimeSpaceArc] = []
    for edge_idx, (u, v) in enumerate(network.edges):
        for depart_idx in range(horizon_index):
            steps = duration_to_time_steps(sample_times[depart_idx, edge_idx], time_step)
            arrival_idx = depart_idx + steps
            if arrival_idx > horizon_index:
                continue
            arcs.append(
                TimeSpaceArc(
                    tail=(u, depart_idx),
                    head=(v, arrival_idx),
                    edge_idx=edge_idx,
                    elapsed_time=steps * float(time_step),
                    arrival_index=arrival_idx,
                )
            )

    sink = "sink"
    for t_idx in range(horizon_index + 1):
        arcs.append(
            TimeSpaceArc(
                tail=(destination, t_idx),
                head=sink,
                edge_idx=None,
                elapsed_time=0.0,
                arrival_index=t_idx,
            )
        )
    return arcs


def _max_reachable_elapsed_time(
    arcs: list[TimeSpaceArc],
    source: tuple[int, int],
    sink: str,
) -> float:
    """Return a sample-specific valid upper bound for selected path elapsed time."""

    def tail_sort_key(arc: TimeSpaceArc) -> tuple[int, int]:
        if isinstance(arc.tail, str):
            return (10**9, 0)
        return (arc.tail[1], 0 if arc.edge_idx is not None else 1)

    distance: dict[tuple[int, int] | str, float] = {source: 0.0}
    for arc in sorted(arcs, key=tail_sort_key):
        if arc.tail not in distance:
            continue
        candidate = distance[arc.tail] + float(arc.elapsed_time)
        if candidate > distance.get(arc.head, -math.inf):
            distance[arc.head] = candidate
    return float(distance.get(sink, 0.0))


def _time_space_nodes(
    network: RoadNetwork,
    horizon_index: int,
    sink: str,
) -> list[tuple[int, int] | str]:
    nodes: list[tuple[int, int] | str] = [
        (node, t_idx)
        for node in network.nodes
        for t_idx in range(horizon_index + 1)
    ]
    nodes.append(sink)
    return nodes


def _node_name(node: tuple[int, int] | str) -> str:
    if isinstance(node, str):
        return node
    return f"{node[0]}_{node[1]}"


def _failure_result(status: str, tau: float, time_step: float) -> dict[str, Any]:
    return {
        "path_x": None,
        "path_edges": None,
        "lateness_count": None,
        "on_time_count": None,
        "punctuality_prob": None,
        "sample_travel_times": None,
        "arrival_time_indices": None,
        "threshold": float(tau),
        "time_step": float(time_step),
        "status": status,
        "solve_time": 0.0,
        "conclusion": None,
    }


def _build_conclusion(
    path_edges: list[tuple[int, int]],
    punctuality_prob: float,
    tau: float,
    on_time_count: int,
    num_samples: int,
) -> str:
    return (
        "Yang_OTAP_ILP found path "
        f"{path_edges} with on-time probability {punctuality_prob:.6g} "
        f"under threshold {tau:.6g}; {on_time_count}/{num_samples} samples arrive on time."
    )
