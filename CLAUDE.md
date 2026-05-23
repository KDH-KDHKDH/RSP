# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RSP (Reliable Shortest Path) — research project reproducing **Cao et al. (2020)** : an ILP-based exact solver for finding the path with maximum probability of arriving on-time given stochastic edge travel times.

The active implementation is in `Cao_SOTA_MP/`. `YangLixing_SOTA_TimeDependent/` is an empty placeholder for future time-dependent SOTA work.

## Commands

```bash
# Generate experiment data
uv run python Cao_SOTA_MP/data/generate.py --preset small              # small debug dataset (10 nodes)
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42     # 65-node, N=500 dataset
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 123
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 456

# Run experiments
uv run python Cao_SOTA_MP/run.py                                                      # default (data/small)
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot       # full experiment with figures
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/artificial_n500.yaml --data-dir Cao_SOTA_MP/data/full/seed42

# Run tests
uv run pytest Cao_SOTA_MP/tests/ -v
```

## Architecture

### Data flow

```
data/generate.py  ──→  data/{preset}/seed{N}/
                        ├── network.npz       (graph topology)
                        ├── travel_times.npz  (W matrices per repeat)
                        ├── od_pairs.npy      (origin-destination pairs)
                        └── meta.yaml         (generation parameters)
                                           │
                                           ▼
run.py  ──→  src/experiment.py  ──→  for each (repeat, OD pair, alpha):
                                      1. compute_deadline(τ) from W and α
                                      2. solve_ilp()        → ground-truth
                                      3. solve_milp()        → ℓ₁ relaxation
                                      4. solve_dijkstra()    → mean shortest path baseline
                                    ──→  results.csv + figures
```

### Solver hierarchy

| Solver | File | Role |
|--------|------|------|
| **ILP** | `src/ilp_solver.py` | Exact solution (binary ιᵢ indicators). Serves as ground-truth for accuracy evaluation. |
| **MILP** | `src/milp_solver.py` | ℓ₁-norm relaxation (continuous pᵢ ≥ Wᵢ'x - τ). Approximate but potentially faster. |
| **Dijkstra** | `src/dijkstra_solver.py` | Baseline: shortest path on mean edge weights, then evaluate punctuality post-hoc. |

All solvers share the same interface: they take `(network, W, origin, destination, tau)` and return `{path_x, punctuality_prob, status, solve_time}`.

### Key modules

- **`src/graph.py`** — `RoadNetwork` dataclass wrapping `nx.DiGraph`. Builds node-arc incidence matrix `M` and OD vector `b` for the flow conservation constraint `Mx = b`.
- **`src/generator.py`** — Random graph generation (spanning tree + random edges), lognormal travel times, deadline computation via K-shortest paths.
- **`src/experiment.py`** — Orchestration: loads pre-generated data, iterates over (repeat × OD pair × alpha), runs all 3 solvers, collects results into a pandas DataFrame.
- **`src/visualize.py`** — Paper-style figures: accuracy vs α, punctuality probability scatter plots.
- **`data/generate.py`** — Standalone data generation entry point with `--preset` support.
- **`run.py`** — Single experiment entry point. `--data-dir` overrides config, `--plot` enables figure output.

### Config system

YAML-based (`configs/*.yaml`). Key sections:
- `data.dir` — path to pre-generated data (overridable via `--data-dir`)
- `experiment.alphas` — deadline levels [0.5, 0.6, 0.7, 0.8, 0.9]
- `solver.backend` — PuLP solver: `HiGHS`, `CBC`, `GLPK`, `SCIP`

### Design decisions

- **ILP is ground-truth** — no path enumeration needed for accuracy evaluation on large graphs.
- **Data generation is separate from solving** — `data/generate.py` produces self-contained directories that `run.py` consumes. This isolates graph topology issues from solver issues.
- **HiGHS is the preferred solver** — ~5x faster than CBC for ILP on 65-node graphs with N=500.
- **Flat `src/`** — no nested subpackages; all modules import from `src.*` with a `sys.path.insert` in entry scripts.
- **Shared venv at RSP level** — managed by `uv` with `pyproject.toml` at repo root.
