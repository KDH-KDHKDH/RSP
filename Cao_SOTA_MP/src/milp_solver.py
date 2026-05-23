"""MILP approximate solver (ℓ₁-norm relaxation) for the punctuality problem."""

import numpy as np
import pulp
from .graph import RoadNetwork
from .ilp_solver import _get_solver


def solve_milp(network: RoadNetwork, W: np.ndarray, origin: int, destination: int,
               tau: float, solver_name: str = "CBC", time_limit: int = 60) -> dict:
    """Solve the punctuality problem approximately via MILP (ℓ₁-norm relaxation).

    min  Σ pᵢ
    s.t. pᵢ ≥ Wᵢ'x - τ,  ∀i
         pᵢ ≥ 0
         Mx = b
         x ∈ {0,1}

    Returns:
        dict with keys: path_x, punctuality_prob, status, solve_time
    """
    N, num_edges = W.shape
    num_nodes = network.num_nodes
    M = network.incidence_matrix()
    b = network.od_vector(origin, destination)

    prob = pulp.LpProblem("Punctuality_MILP", pulp.LpMinimize)

    # Decision variables
    x = [pulp.LpVariable(f"x_{j}", cat="Binary") for j in range(num_edges)]
    p = [pulp.LpVariable(f"p_{i}", lowBound=0, cat="Continuous") for i in range(N)]

    # Objective: min Σ pᵢ
    prob += pulp.lpSum(p)

    # Delay constraints: pᵢ ≥ Wᵢ'x - τ
    for i in range(N):
        prob += (
            p[i] >= pulp.lpSum(W[i, j] * x[j] for j in range(num_edges)) - tau,
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
    try:
        prob.solve(solver)
    except Exception as e:
        return {"path_x": None, "punctuality_prob": None,
                "status": f"SolverError: {e}", "solve_time": 0.0}

    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        return {"path_x": None, "punctuality_prob": None,
                "status": status, "solve_time": prob.solutionTime}

    path_x = np.array([v.varValue for v in x])

    # Compute actual punctuality probability for the chosen path
    path_travel_times = W @ path_x
    lateness_count = np.sum(path_travel_times > tau)
    punctuality_prob = 1.0 - lateness_count / N

    return {
        "path_x": path_x,
        "punctuality_prob": punctuality_prob,
        "status": status,
        "solve_time": prob.solutionTime,
    }
