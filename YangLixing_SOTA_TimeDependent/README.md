# YangLixing_SOTA_TimeDependent - Time-Dependent OTAP

This folder contains the Yang and Zhou time-dependent reliable path reproduction work. The first implemented method is `Yang_OTAP_ILP`, exposed through the shared root SDK as `RSPTimeDependentDataset` + `RSPRunner`.

## Current Scope

- Implemented: OTAP exact ILP on sample-based time-expanded networks.
- Not implemented yet: PTT, PSTOTAP, Lagrangian relaxation, static fallback mode.
- Public method name: `Yang_OTAP_ILP`.
- Public SDK entry: root package `rsp`.
- Notebook example: `notebook/td.ipynb`.

The first-version data strategy reuses Cao static samples and creates simulated time-dependent samples:

```text
TD[sample, time_step, edge] = W[sample, edge] * time_profile[time_step]
```

The deadline uses the existing Cao `alpha -> tau` mechanism on `td.deadline_matrix()`, which is the mean over the time dimension.

## Project Layout

```text
YangLixing_SOTA_TimeDependent/
├── src/
│   ├── __init__.py
│   └── yang_otap_solver.py          # Core exact OTAP ILP
├── tests/
│   └── test_yang_otap_solver.py     # Toy network and input validation tests
├── configs/                         # Reserved for Yang configs
├── data/                            # Reserved for Yang data artifacts
├── results/                         # Local experiment outputs
└── README.md
```

`docs/` is intentionally not tracked, following the Cao project style. Keep the paper PDF, plan/spec/todo/change logs, and generated HTML reports there locally.

## SDK Usage

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
print(result.status_counts())
```

For single-case debugging:

```python
runner = RSPRunner(td, config)
case = runner.solve_case(repeat=0, od_idx=0, alpha=0.7)
metrics = case.metrics["methods"]["Yang_OTAP_ILP"]
print(case.tau)
print(metrics["punctuality_prob"], metrics["status"], metrics["solve_time"])
print(metrics["path_edges"])
```

## Horizon Behavior

`RSPTimeDependentDataset.from_cao_dataset(..., auto_horizon=True)` is the default. It extends the provided `time_profile` when needed so selected OD/sample cases have enough time-expanded horizon. Extension repeats the last profile factor and records metadata:

- `auto_horizon`
- `input_time_profile_length`
- `time_profile_length`
- `auto_horizon_added_steps`
- `auto_horizon_padding_steps`

Interactive notebooks should still keep sample counts and OD counts modest. The exact Yang model grows with `samples x time_steps x edges`.

## Performance Expectation

`Yang_OTAP_ILP` is an exact time-expanded ILP and is normally much slower than Cao static `ILP`. On the current notebook audit result with 4 OD / 8 rows and 50 samples, Yang was roughly `14x-437x` slower than Cao static ILP on the same OD/sample scale. This is expected because Yang adds sample-specific time-space path variables, time-space flow constraints, and physical/time-space linking constraints.

## Validation

Focused checks:

```bash
uv run pytest YangLixing_SOTA_TimeDependent/tests/test_yang_otap_solver.py -v
uv run pytest Cao_SOTA_MP/tests/test_sdk.py -k 'time_dependent_dataset_from_cao_dataset or yang' -v
python3 -m json.tool notebook/td.ipynb >/dev/null
```

Full Cao regression:

```bash
uv run pytest Cao_SOTA_MP/tests/ -v
```

## References

- Yang and Zhou (2017). Time-dependent reliable path finding with OTAP/PTT formulations.
- Cao et al. (2020). Static stochastic reliable shortest path formulation reused here for datasets, deadlines, and SDK metrics.
