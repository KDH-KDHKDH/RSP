"""ILP exact solver for the punctuality problem (core algorithm)."""

import time

import numpy as np
import pulp
from .graph import RoadNetwork


def _new_variable(name: str, low_bound=None, up_bound=None, cat="Continuous"):
    """Create a PuLP variable without triggering PuLP 4.0 deprecation warnings.

    The installed PuLP version exposes ``prob.add_variable(...)`` but still forwards the
    deprecation-suppression flag positionally, so warning noise remains. Use the explicit
    keyword until the upstream helper is fixed.
    """
    return pulp.LpVariable(
        name,
        lowBound=low_bound,
        upBound=up_bound,
        cat=cat,
        _skip_v4_deprecation=True,
    )


def solve_ilp(network: RoadNetwork, W: np.ndarray, origin: int, destination: int,
              tau: float, big_m: float = 1e6, solver_name: str = "CBC",
              time_limit: int = 60) -> dict:
    """Solve the punctuality problem exactly via ILP.

    min  Σ ιᵢ
    s.t. Σⱼ Wᵢⱼ·xⱼ - Mᵢ·ιᵢ ≤ τ,  ∀i
         Mx = b
         x ∈ {0,1}, ι ∈ {0,1}

    Uses per-sample tight big-M: Mᵢ = min(big_m, max(1.0, ΣⱼW[i,j] - τ)).
    This is 200-8000x smaller than a fixed big-M, giving tighter LP relaxation.

    Args:
        network: Road network
        W: Travel time samples (N x |L|)
        origin: Origin node
        destination: Destination node
        tau: Deadline
        big_m: Big-M cap (used as upper bound for per-sample Mᵢ)
        solver_name: PuLP solver backend (CBC, GLPK, CPLEX, SCIP)
        time_limit: Solver time limit in seconds

    Returns:
        dict with keys: path_x, lateness_count, punctuality_prob, status, solve_time
    """
    N, num_edges = W.shape
    num_nodes = network.num_nodes
    M = network.incidence_matrix()
    b = network.od_vector(origin, destination)

    # Create problem
    prob = pulp.LpProblem("Punctuality_ILP", pulp.LpMinimize)

    # Decision variables
    x = [_new_variable(f"x_{j}", cat="Binary") for j in range(num_edges)]
    iota = [_new_variable(f"iota_{i}", cat="Binary") for i in range(N)]

    # Objective: min Σ ιᵢ
    prob += pulp.lpSum(iota)

    # Delay indicator constraints: Wᵢ'x - Mᵢ·ιᵢ ≤ τ
    # Per-sample tight M: worst-case path time (sum of all edge times) - tau
    # Falls back to big_m cap for safety
    for i in range(N):
        Mi = max(1.0, float(np.sum(W[i, :]) - tau))
        Mi = min(Mi, big_m)
        prob += (
            pulp.lpSum(W[i, j] * x[j] for j in range(num_edges)) - Mi * iota[i] <= tau,
            f"delay_{i}"
        )

    # Flow conservation: Mx = b
    for v in range(num_nodes):
        prob += (
            pulp.lpSum(M[v, j] * x[j] for j in range(num_edges)) == b[v],
            f"flow_{v}"
        )

    # Solve
    solver = _get_solver(solver_name, time_limit)
    t0 = time.perf_counter()
    try:
        prob.solve(solver)
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return {"path_x": None, "lateness_count": None,
                "punctuality_prob": None, "status": f"SolverError: {e}", "solve_time": elapsed}
    elapsed = time.perf_counter() - t0

    # Extract results
    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        return {"path_x": None, "lateness_count": None,
                "punctuality_prob": None, "status": status, "solve_time": elapsed}

    path_x = np.array([v.varValue for v in x])
    lateness_count = sum(v.varValue for v in iota)
    punctuality_prob = 1.0 - lateness_count / N

    return {
        "path_x": path_x,
        "lateness_count": int(lateness_count),
        "punctuality_prob": punctuality_prob,
        "status": status,
        "solve_time": elapsed,
    }


def _get_solver(name: str, time_limit: int):
    name = name.upper()
    if name == "CBC":
        return pulp.PULP_CBC_CMD(msg=0, timeLimit=time_limit)
    elif name == "GLPK":
        return pulp.GLPK_CMD(msg=0, options=["--tmlim", str(time_limit)])
    elif name == "CPLEX":
        return pulp.CPLEX_CMD(msg=0, timelimit=time_limit)
    elif name == "HIGHS":
        return pulp.HiGHS(msg=0, timeLimit=time_limit)
    elif name == "SCIP":
        return pulp.SCIP_PY(msg=0, timeLimit=time_limit)
    else:
        return pulp.PULP_CBC_CMD(msg=0, timeLimit=time_limit)
