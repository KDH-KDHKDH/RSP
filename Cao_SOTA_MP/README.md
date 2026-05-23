# RSP: Reliable Shortest Path

Reproduction of **Cao et al. (2020)** — an ILP-based exact solver for finding the path
with maximum probability of arriving on-time under stochastic edge travel times.

## Quick Start

```bash
# Install dependencies
uv sync

# Generate experiment data (preset: small / full)
uv run python Cao_SOTA_MP/data/generate.py --preset small
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42

# Run experiment
uv run python Cao_SOTA_MP/run.py                                                # small dataset (default)
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot # full dataset with figures

# Run tests
uv run pytest Cao_SOTA_MP/tests/ -v
```

## Solvers

| Solver | File | Description |
|--------|------|-------------|
| **ILP** | `src/ilp_solver.py` | Exact solution via binary lateness indicators + Big-M constraints |
| **MILP** | `src/milp_solver.py` | L1-norm relaxation with continuous penalty variables |
| **Dijkstra** | `src/dijkstra_solver.py` | Mean shortest path baseline |

All solvers take `(network, W, origin, destination, tau)` and return `{path_x, punctuality_prob, status, solve_time}`.

## Current Results (seed42, CV=0.54)

| Method | Accuracy | Solve Time (mean) |
|--------|----------|-------------------|
| ILP | **100.0%** | 0.50s |
| Dijkstra | 83.5% | 0.0003s |
| MILP | 73.8% | 0.17s |

ILP = 100% accuracy reproduced. ILP outperforms Dijkstra by +16.5pp and MILP by +26.2pp.

## Project Structure

```
Cao_SOTA_MP/
├── data/                # Generated datasets (small / full/seed*)
│   └── generate.py      # Data generation entry point
├── configs/             # YAML experiment configs
├── src/                 # Source code (flat package)
│   ├── graph.py         # RoadNetwork + incidence matrix
│   ├── generator.py     # Graph/travel-time generation + deadline
│   ├── ilp_solver.py    # ILP exact solver
│   ├── milp_solver.py   # MILP relaxation
│   ├── dijkstra_solver.py  # Dijkstra baseline
│   ├── experiment.py    # Experiment orchestration
│   └── visualize.py     # Accuracy vs α + scatter plots
├── tests/               # 10 unit tests
├── docs/                # Plans, specs, changelog, result reports
├── results/             # Experiment outputs (CSV + figures)
├── run.py               # Single experiment entry point
└── todo.md              # Current task list
```

## Configuration

Switch datasets via `--data-dir`:

```bash
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/artificial_n500.yaml --data-dir Cao_SOTA_MP/data/full/seed42
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/artificial_n500.yaml --data-dir Cao_SOTA_MP/data/full/seed99
```

## Key Design Decisions

- **ILP is ground-truth** — no path enumeration needed for accuracy evaluation
- **Data generation is separate from solving** — `data/generate.py` produces self-contained directories
- **SCIP solver** (pyscipopt 6.2.1) — open-source, stable (HiGHS has memory corruption bug)
- **Path-vector match** — accuracy checks `np.array_equal(path, ref_path)`, not probability equality
- **Shared venv** at repo root — managed by `uv` with `pyproject.toml`

## References

- Cao, Z., Guo, H., Zhang, J., Niyato, D., & Fastenrath, U. (2020). Finding the Shortest Path with Maximum Punctuality Probability under Stochastic Travel Times. *IEEE Transactions on Intelligent Transportation Systems*.
