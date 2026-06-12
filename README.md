# RSP - Reliable Shortest Path

This repository provides a shared Python SDK for reliable shortest path experiments, with two reproduced method families:

- `Cao_SOTA_MP`: Cao et al. stochastic reliable shortest path solvers on static travel-time samples.
- `YangLixing_SOTA_TimeDependent`: Yang and Zhou time-dependent OTAP solver on sample-based time-expanded networks.

The public API lives in the root `rsp/` package. Research-specific folders keep the core solver implementations, tests, generated datasets, and local reports.

## Project Layout

```text
RSP/
├── rsp/                              # Public SDK facade
│   ├── __init__.py                   # RSPDataset, RSPTimeDependentDataset, RSPConfig, RSPRunner, RSPResult
│   ├── dataset.py                    # Static and time-dependent dataset containers
│   ├── config.py                     # Typed experiment config
│   ├── runner.py                     # Single-case and batch execution
│   ├── result.py                     # Tabular result summaries
│   ├── metrics.py                    # Shared metrics
│   └── adapters/                     # Calls into Cao/Yang core solvers
│
├── Cao_SOTA_MP/                      # Cao et al. static stochastic RSP reproduction
│   ├── src/                          # ILP, MILP, Dijkstra and experiment utilities
│   ├── data/                         # Data generator and generated datasets
│   ├── configs/                      # YAML experiment configs
│   ├── tests/                        # Cao and SDK regression tests
│   └── run.py                        # CLI entry point
│
├── YangLixing_SOTA_TimeDependent/    # Yang and Zhou time-dependent OTAP reproduction
│   ├── src/yang_otap_solver.py       # Exact OTAP time-expanded ILP
│   ├── tests/                        # Core Yang solver tests
│   ├── configs/                      # Reserved for Yang configs
│   ├── data/                         # Reserved for Yang data artifacts
│   └── results/                      # Local experiment outputs
│
└── notebook/
    ├── mp.ipynb                      # Cao SDK example
    └── td.ipynb                      # Yang SDK example and small experiment platform
```

`Cao_SOTA_MP/docs/` and `YangLixing_SOTA_TimeDependent/docs/` are intentionally ignored by git. They are local maintenance/report folders and may contain large PDFs or generated HTML reports.

## Setup

```bash
uv sync
```

Run the focused validation suite:

```bash
uv run pytest Cao_SOTA_MP/tests/test_sdk.py -k 'time_dependent_dataset_from_cao_dataset or yang' -v
uv run pytest YangLixing_SOTA_TimeDependent/tests/test_yang_otap_solver.py -v
```

Run all Cao tests:

```bash
uv run pytest Cao_SOTA_MP/tests/ -v
```

## Cao Static SDK Example

```python
from rsp import RSPConfig, RSPDataset, RSPRunner

dataset = RSPDataset.from_directory("Cao_SOTA_MP/data/small")
config = RSPConfig(
    methods=("ILP", "MILP", "Dijkstra"),
    alphas=(0.5, 0.7, 0.9),
    num_repeats=1,
    num_od_pairs=3,
    solver_backend="SCIP",
)

result = RSPRunner(dataset, config).run()
print(result.summary())
print(result.by_alpha())
```

## Yang Time-Dependent SDK Example

Yang first-version support implements OTAP only. It reuses a Cao static dataset by lifting `W[sample, edge]` into a time-dependent tensor:

```text
TD[sample, time_step, edge] = W[sample, edge] * time_profile[time_step]
```

The SDK computes the Cao-style deadline from the mean-over-time matrix and then solves `Yang_OTAP_ILP` on the time-expanded samples.

```python
import numpy as np

from rsp import RSPConfig, RSPDataset, RSPRunner, RSPTimeDependentDataset

cao = RSPDataset.from_directory("Cao_SOTA_MP/data/full/seed524")
td = RSPTimeDependentDataset.from_cao_dataset(
    cao,
    time_profile=np.array([1.0, 1.05, 0.95, 1.1]),
    time_step=0.05,
    auto_horizon=True,
)

config = RSPConfig(
    methods=("Yang_OTAP_ILP",),
    alphas=(0.5, 0.7),
    num_repeats=1,
    num_od_pairs=2,
    solver_backend="SCIP",
    time_limit=60,
)

result = RSPRunner(td, config).run()
print(result.summary())
print(result.by_od())
```

For a fuller interactive example, use `notebook/td.ipynb`. It shows network loading, single OD metrics, multi OD metrics, and CSV exports.

## Methods

| Method | Dataset | Description |
|--------|---------|-------------|
| `ILP` | `RSPDataset` | Cao exact static stochastic RSP solver with binary lateness indicators |
| `MILP` | `RSPDataset` | Cao L1 relaxation baseline |
| `Dijkstra` | `RSPDataset` | Mean-travel-time shortest path baseline |
| `Yang_OTAP_ILP` | `RSPTimeDependentDataset` | Yang exact time-dependent OTAP solver on a time-expanded network |

`Yang_OTAP_ILP` is expected to be much slower than Cao static `ILP` because it adds sample-specific time-space flow variables and linking constraints. The current notebook audit on 4 OD / 8 rows found a slowdown of roughly `14x-437x` versus Cao static ILP on the same OD/sample scale.

## Result Accessors

`RSPResult` exposes stable tabular summaries:

```python
df = result.to_dataframe()
result.summary()
result.by_alpha()
result.by_od()
result.solve_time()
result.status_counts()
result.save_csv("results.csv")
```

When static `ILP` is included as a reference, `method_comparison(reference="ILP")`, tie-aware accuracy, path-match accuracy, and objective gaps are available. For Yang-only runs, use punctuality probability, lateness counts, status, path length, and solve-time metrics.

## References

- Cao, Z., Guo, H., Zhang, J., Niyato, D., & Fastenrath, U. (2020). Finding the Shortest Path with Maximum Punctuality Probability under Stochastic Travel Times. IEEE Transactions on Intelligent Transportation Systems.
- Yang and Zhou (2017). Time-dependent reliable path finding with OTAP/PTT formulations.
