# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RSP (Reliable Shortest Path) — research project reproducing **Cao et al. (2020)** : an ILP-based exact solver for finding the path with maximum probability of arriving on-time given stochastic edge travel times.

The active implementation is in `Cao_SOTA_MP/`. `YangLixing_SOTA_TimeDependent/` is an empty placeholder for future time-dependent SOTA work.

## Commands

```bash
# Generate experiment data
uv run python Cao_SOTA_MP/data/generate.py --preset small              # small debug dataset (10 nodes)
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42     # 65-node, N=500 dataset (default seed)
uv run python Cao_SOTA_MP/data/generate.py --preset beijing            # Beijing OSM road network

# Run experiments
uv run python Cao_SOTA_MP/run.py                                                      # default (data/small)
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot       # full experiment with figures
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/beijing.yaml --data-dir Cao_SOTA_MP/data/beijing --plot

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
- **`src/generator.py`** — Random graph generation (spanning tree + random edges), lognormal travel times, deadline computation via K-shortest paths. Also handles Beijing OSM attribute-driven generation.
- **`src/osm_network.py`** — Loads Beijing OSM road network from pre-extracted GraphML (587 nodes, 1066 edges, central Beijing major roads). Uses osmium for offline PBF parsing instead of osmnx Overpass API (blocked by GFW).
- **`src/experiment.py`** — Orchestration: loads pre-generated data, iterates over (repeat × OD pair × alpha), runs all 3 solvers, collects results into a pandas DataFrame.
- **`src/visualize.py`** — Paper-style figures: accuracy vs α, punctuality probability scatter plots.
- **`data/generate.py`** — Standalone data generation entry point with `--preset` support.
- **`run.py`** — Single experiment entry point. `--data-dir` overrides config, `--plot` enables figure output.

### Config system

YAML-based (`configs/*.yaml`). Key sections:
- `data.dir` — path to pre-generated data (overridable via `--data-dir`)
- `experiment.alphas` — deadline levels [0.5, 0.6, 0.7, 0.8, 0.9]
- `solver.backend` — PuLP solver: `SCIP`, `CBC`, `GLPK`

### Design decisions

- **ILP is ground-truth** — no path enumeration needed for accuracy evaluation on large graphs.
- **Data generation is separate from solving** — `data/generate.py` produces self-contained directories that `run.py` consumes. This isolates graph topology issues from solver issues.
- **SCIP is the preferred solver** — stable open-source solver via pyscipopt 6.2.1. HiGHS was abandoned due to a memory corruption bug.
- **Flat `src/`** — no nested subpackages; all modules import from `src.*` with a `sys.path.insert` in entry scripts.
- **Shared venv at RSP level** — managed by `uv` with `pyproject.toml` at repo root.

## Documentation Rules

Each file under `docs/` has a specific scope. When modifying the project, keep these documents in sync:

| Document | Purpose | When to Update |
|----------|---------|----------------|
| `docs/change.md` | Chronological changelog | **Every change** — add dated entry at top; newest first |
| `docs/handover/` | Onboarding for next person/agent | Major milestones or when handing off |
| `docs/report/` | Numbered HTML experiment reports | New experiment results or project audits |
| `docs/plan.md` | High-level roadmap, phases, key decisions | Phases complete or direction changes |
| `docs/todo.md` | Granular actionable tasks (priority-sorted) | Tasks added, completed, or reprioritized |
| `docs/spec.md` | Authoritative spec: interfaces, algorithms, acceptance criteria | Interfaces, dependencies, or acceptance thresholds change |

**Rules:**
- `report/` files are HTML with embedded CSS — polished, self-contained, color-coded callout boxes
- `report/` files are immutable once numbered — create a new report for new results
- `plan.md` stays broad (phases + decisions), `todo.md` stays granular (concrete actions + shell commands)
- `spec.md` defines "done" — no implementation details or TODO items
- `change.md` entries are dated, grouped, factual — describe what changed and why

## Git Rules

- Never add `Co-Authored-By` or similar trailers to commit messages
- Use concise, descriptive commit messages in English
- Follow existing commit style: short subject line, optional body with bullet points
