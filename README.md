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

## SDK Overview

SDK 的统一入口是根目录包 `rsp`。通常只需要导入 4 个对象:

```python
from rsp import RSPConfig, RSPDataset, RSPRunner, RSPTimeDependentDataset
```

推荐工作流:

1. 用 `RSPDataset` 或 `RSPTimeDependentDataset` 准备 network、travel times、OD pairs。
2. 用 `RSPConfig` 选择方法、alpha、repeat/OD 数量、solver 和 time limit。
3. 用 `RSPRunner(dataset, config)` 运行单个 case 或批量实验。
4. 用 `RSPResult` 读取 summary、by alpha、by OD、status、solve time，并导出 CSV。

### SDK Object Map

| Object | 用途 | 典型输入 |
|--------|------|----------|
| `RSPDataset` | Cao 静态随机旅行时间数据容器 | `W[sample, edge]` 或 `W[repeat, sample, edge]` |
| `RSPTimeDependentDataset` | Yang 时变旅行时间数据容器 | `TD[sample, time_step, edge]` 或 `TD[repeat, sample, time_step, edge]` |
| `RSPConfig` | 实验配置 | methods, alphas, solver, time limit, repeat/OD cap |
| `RSPRunner` | 单 case / 批量运行入口 | dataset + config |
| `RSPResult` | 表格结果和聚合指标 | pandas DataFrame |

### Method And Dataset Compatibility

| Method | Dataset | 说明 |
|--------|---------|------|
| `ILP` | `RSPDataset` 或 `RSPTimeDependentDataset` | Cao exact static ILP；若传入 TD dataset，内部使用 `deadline_matrix()` 聚合为静态矩阵 |
| `MILP` | `RSPDataset` 或 `RSPTimeDependentDataset` | Cao L1 relaxation baseline |
| `Dijkstra` | `RSPDataset` 或 `RSPTimeDependentDataset` | 均值最短路 baseline |
| `Yang_OTAP_ILP` | `RSPTimeDependentDataset` only | Yang exact time-dependent OTAP；需要完整时变张量 |

`Yang_OTAP_ILP` 是 exact time-expanded ILP，通常显著慢于 Cao static `ILP`。当前 notebook 审计的 4 OD / 8 rows、50 samples 结果中，Yang 比 Cao static ILP 慢约 `14x-437x`。这是模型规模差异导致的正常现象。

## Static SDK: Cao Methods

### Load A Generated Dataset

Cao 数据目录包含:

```text
network.npz
travel_times.npz
od_pairs.npy
meta.yaml
```

读取方式:

```python
from rsp import RSPDataset

dataset = RSPDataset.from_directory("Cao_SOTA_MP/data/full/seed524")

print(dataset.network.num_nodes)
print(dataset.network.num_edges)
print(dataset.num_repeats)
print(dataset.num_od_pairs)
print(dataset.od_pairs[:5])
```

### Build A Dataset From Arrays

如果你已经有自己的 NetworkX 图、样本矩阵和 OD，可以直接从内存构建:

```python
import networkx as nx
import numpy as np

from rsp import RSPDataset

graph = nx.DiGraph()
graph.add_edges_from([
    (0, 1),
    (1, 3),
    (0, 2),
    (2, 3),
])

num_samples = 100
num_edges = graph.number_of_edges()
W = np.random.lognormal(mean=0.0, sigma=0.3, size=(num_samples, num_edges))
od_pairs = [(0, 3)]

dataset = RSPDataset.from_networkx(
    graph=graph,
    travel_times=W,
    od_pairs=od_pairs,
)
```

`W` 的列顺序必须和 `dataset.edge_order` 一致。若你的旅行时间矩阵已经按某个固定边顺序排列，请显式传入:

```python
edge_order = [(0, 1), (1, 3), (0, 2), (2, 3)]
dataset = RSPDataset.from_networkx(graph, W, od_pairs, edge_order=edge_order)
```

### Run A Single OD Case

单 case 适合调试一个 OD、一个 alpha:

```python
from rsp import RSPConfig, RSPRunner

config = RSPConfig(
    methods=("ILP", "MILP", "Dijkstra"),
    alphas=(0.7,),
    solver_backend="SCIP",
    time_limit=60,
)

runner = RSPRunner(dataset, config)
case = runner.solve_case(repeat=0, od_idx=0, alpha=0.7)

print("tau:", case.tau)
for method, metrics in case.metrics["methods"].items():
    print(method)
    print("  status:", metrics["status"])
    print("  punctuality:", metrics["punctuality_prob"])
    print("  late:", metrics["lateness_count"])
    print("  path:", metrics["path_edges"])
    print("  solve_time:", metrics["solve_time"])
```

也可以不用 `od_idx`，直接指定起终点:

```python
case = runner.solve_case(repeat=0, origin=13, destination=35, alpha=0.7)
```

### Run Multi OD / Multi Alpha

批量运行会遍历:

```text
repeat in range(num_repeats)
od_idx in range(num_od_pairs)
alpha in config.alphas
method in config.methods
```

示例:

```python
config = RSPConfig(
    methods=("ILP", "MILP", "Dijkstra"),
    alphas=(0.5, 0.7, 0.9),
    num_repeats=1,
    num_od_pairs=5,
    solver_backend="SCIP",
    time_limit=60,
)

result = RSPRunner(dataset, config).run(progress=True)

print(result.summary())
print(result.by_alpha())
print(result.by_od())
print(result.status_counts())
```

### Compare Against ILP

如果配置里包含 `ILP`，SDK 会把 `ILP` 作为 reference，自动给其他方法计算:

- `objective_gap`
- `tie_aware_correct`
- `correct` / path-match correctness

```python
comparison = result.method_comparison(reference="ILP")
print(comparison[[
    "repeat",
    "od_idx",
    "alpha",
    "method",
    "method_punctuality_prob",
    "reference_punctuality_prob",
    "objective_gap",
    "tie_aware_correct",
]])
```

## Time-Dependent SDK: Yang OTAP

Yang 首版只实现 `Yang_OTAP_ILP`。输入是时变旅行时间张量:

```text
TD[sample, time_step, edge]
```

如果有多个 repeat，则可以传:

```text
TD[repeat, sample, time_step, edge]
```

### Reuse A Cao Dataset

当前推荐方式是复用 Cao 数据，通过时间曲线构造时变张量:

```text
TD[sample, time_step, edge] = W[sample, edge] * time_profile[time_step]
```

示例:

```python
import numpy as np

from rsp import RSPConfig, RSPDataset, RSPRunner, RSPTimeDependentDataset

cao = RSPDataset.from_directory("Cao_SOTA_MP/data/full/seed524")

td_dataset = RSPTimeDependentDataset.from_cao_dataset(
    cao,
    time_profile=np.array([1.0, 1.05, 0.95, 1.10]),
    time_step=0.05,
    auto_horizon=True,
    horizon_padding_steps=0,
)

print(td_dataset.num_samples)
print(td_dataset.num_time_steps)
print(td_dataset.meta)
```

`auto_horizon=True` 是默认值。它会在 SDK 内部根据 OD、样本旅行时间、`time_step` 和 `time_profile` 自动扩展 horizon，避免用户手工猜 `T`。扩展方式是重复最后一个 profile factor，并在 `td_dataset.meta` 中记录:

- `auto_horizon`
- `input_time_profile_length`
- `time_profile_length`
- `auto_horizon_added_steps`
- `auto_horizon_padding_steps`

### Build Time-Dependent Data From Arrays

如果你已经有时变张量:

```python
td_dataset = RSPTimeDependentDataset.from_arrays(
    network=dataset.network,
    travel_times=td_tensor,          # shape: (samples, time_steps, edges)
    od_pairs=[(13, 35), (11, 24)],
    time_step=0.05,
)
```

`travel_times` 也可以是 4D:

```python
td_tensor.shape == (num_repeats, num_samples, num_time_steps, num_edges)
```

### Build Time-Dependent Data From NetworkX Attributes

如果你的 NetworkX 边上已经有 `mean_time`，以及 `sigma` 或 `cv`，SDK 可以生成 lognormal 样本:

```python
import networkx as nx
import numpy as np

from rsp import RSPTimeDependentDataset

graph = nx.DiGraph()
graph.add_edge(0, 1, mean_time=0.3, cv=0.2)
graph.add_edge(1, 3, mean_time=0.4, cv=0.3)
graph.add_edge(0, 2, mean_time=0.5, sigma=0.25)
graph.add_edge(2, 3, mean_time=0.3, sigma=0.20)

td_dataset = RSPTimeDependentDataset.from_networkx(
    graph=graph,
    od_pairs=[(0, 3)],
    time_profile=np.array([1.0, 1.1, 0.9, 1.0]),
    num_samples=50,
    time_step=0.05,
    random_seed=42,
)
```

### Run Yang Single OD

```python
config = RSPConfig(
    methods=("Yang_OTAP_ILP",),
    alphas=(0.7,),
    solver_backend="SCIP",
    time_limit=60,
)

runner = RSPRunner(td_dataset, config)
case = runner.solve_case(repeat=0, od_idx=0, alpha=0.7)
yang = case.metrics["methods"]["Yang_OTAP_ILP"]

print("tau:", case.tau)
print("status:", yang["status"])
print("punctuality:", yang["punctuality_prob"])
print("late/on-time:", yang["lateness_count"], yang["on_time_count"])
print("path:", yang["path_edges"])
print("path_length:", yang["path_length"])
print("mean_time:", yang["mean_time"])
print("max_delay:", yang["max_delay"])
print("solve_time:", yang["solve_time"])
print("conclusion:", yang["conclusion"])
```

### Run Yang Multi OD

直接批量运行:

```python
config = RSPConfig(
    methods=("Yang_OTAP_ILP",),
    alphas=(0.5, 0.7),
    num_repeats=1,
    num_od_pairs=4,
    solver_backend="SCIP",
    time_limit=120,
)

result = RSPRunner(td_dataset, config).run(progress=True)
print(result.summary())
print(result.by_alpha())
print(result.by_od())
print(result.solve_time())
```

对交互式 notebook，更推荐逐个 OD 构造 one-OD TD dataset，这样每个 OD 都使用自己的自适应 horizon，不会被最难 OD 的最大 `T` 拖慢:

```python
import pandas as pd

source_indices = [18, 19, 1, 2]
rows = []
one_od_config = RSPConfig(
    methods=("Yang_OTAP_ILP",),
    alphas=(0.5, 0.7),
    num_repeats=1,
    num_od_pairs=1,
    solver_backend="SCIP",
    time_limit=120,
)

for source_od_idx in source_indices:
    one_od_cao = RSPDataset.from_arrays(
        network=cao.network,
        travel_times=cao.travel_times,
        od_pairs=[cao.od_pairs[source_od_idx]],
        meta={**cao.meta, "source_od_idx": source_od_idx},
    )
    one_od_td = RSPTimeDependentDataset.from_cao_dataset(
        one_od_cao,
        time_profile=np.array([1.0, 1.05, 0.95, 1.10]),
        time_step=0.05,
        auto_horizon=True,
    )
    runner = RSPRunner(one_od_td, one_od_config)
    one_result = runner.run(progress=False).to_dataframe()
    one_result["source_od_idx"] = source_od_idx
    one_result["td_time_steps"] = one_od_td.num_time_steps
    rows.append(one_result)

df = pd.concat(rows, ignore_index=True)
print(df[["source_od_idx", "origin", "dest", "alpha", "status", "punctuality_prob", "solve_time", "td_time_steps"]])
```

`notebook/td.ipynb` 使用的就是这种思路，适合做网络读取、单 OD 指标、多 OD 指标和 CSV 输出。

## Configuration Reference

`RSPConfig` 常用字段:

| Field | 默认值 | 说明 |
|-------|--------|------|
| `methods` | `("ILP", "MILP", "Dijkstra")` | 要运行的方法 |
| `alphas` | `(0.5, 0.7, 0.9)` | deadline 分位/宽松程度参数 |
| `num_repeats` | `None` | `None` 表示用完 dataset 所有 repeat |
| `num_od_pairs` | `None` | `None` 表示用完 dataset 所有 OD |
| `solver_backend` | `"SCIP"` | PuLP 后端名；常用 `SCIP` 或 `CBC` |
| `big_m` | `1_000_000` | Big-M 上限；Cao ILP 内部也有 per-sample tight-M 逻辑 |
| `time_limit` | `60` | 单个 solver case 的时间限制，单位秒 |
| `deadline_mode` | `"heuristic"` | deadline 计算模式: `heuristic` 或 `exact` |
| `max_candidate_paths` | `1000` | heuristic deadline 候选路径数 |
| `deadline_enumeration_cutoff` | `15` | exact deadline 路径枚举 cutoff |
| `random_seed` | `42` | deadline heuristic 和生成流程使用 |
| `output_dir` | `None` | 调用方可用的输出目录配置 |
| `save_csv` | `False` | 调用方可用的保存开关 |
| `save_figures` | `False` | 调用方可用的画图开关 |

可以从 YAML 读取:

```python
config = RSPConfig.from_yaml("Cao_SOTA_MP/configs/beijing.yaml")
```

也可以保存:

```python
config.to_yaml("configs/my_experiment.yaml")
```

## Result Accessors

批量运行返回 `RSPResult`:

```python
result = RSPRunner(dataset, config).run()
```

常用读取接口:

```python
df = result.to_dataframe()
summary = result.summary()
by_alpha = result.by_alpha()
by_od = result.by_od()
solve_time = result.solve_time()
status = result.status_counts()
```

导出 CSV:

```python
result.save_csv("results.csv")
result.summary().to_csv("summary.csv", index=False)
result.by_alpha().to_csv("by_alpha.csv", index=False)
result.by_od().to_csv("by_od.csv", index=False)
result.status_counts().to_csv("status_counts.csv", index=False)
result.solve_time().to_csv("solve_time.csv", index=False)
```

常见结果列:

| Column | 说明 |
|--------|------|
| `repeat` | repeat index |
| `od_idx` | dataset 内部 OD index |
| `origin`, `dest`, `destination` | 起点和终点 |
| `alpha` | deadline 参数 |
| `tau` | 本 case 的 deadline |
| `method` | 方法名 |
| `status` | solver 状态，如 `Optimal`, `Infeasible`, `TimeLimit` |
| `punctuality_prob` | 准时到达概率 |
| `lateness_count`, `on_time_count` | late / on-time 样本数量 |
| `path_edges` | 选中的物理路径边 |
| `path_length` | 路径边数 |
| `mean_time` | 样本平均旅行时间 |
| `max_delay` | 最大迟到时间 |
| `solve_time` | solver 耗时，单位秒 |
| `reference_available` | 是否有 static `ILP` reference |
| `objective_gap` | 与 reference 的准时概率差距 |
| `tie_aware_correct` | tie-aware accuracy 标记 |
| `correct` | 路径向量是否匹配 reference |
| `conclusion` | 方法生成的可读结论文本 |

## Practical Notes

- 换 network / OD: 只需要构造新的 `RSPDataset` 或 `RSPTimeDependentDataset`，并保证 OD 节点存在且可达。
- 换 travel time: 对 Cao 改 `W[sample, edge]`；对 Yang 改 `TD[sample, time_step, edge]`，或改 Cao `W` 加 `time_profile`。
- 换 alpha: 改 `RSPConfig(alphas=(...))`。
- 单 OD 调试: 用 `runner.solve_case(...)`。
- 多 OD 实验: 用 `runner.run(...)`；Yang 交互式实验建议逐 OD 构造 one-OD dataset 以获得 per-OD horizon。
- Yang 性能: `num_samples`、`num_time_steps`、`num_edges` 都会显著影响速度；`T=70+` 的 OD 应预期明显慢于短 OD。
- docs 目录: `Cao_SOTA_MP/docs/` 和 `YangLixing_SOTA_TimeDependent/docs/` 是本地维护资料，不进入 git。

## References

- Cao, Z., Guo, H., Zhang, J., Niyato, D., & Fastenrath, U. (2020). Finding the Shortest Path with Maximum Punctuality Probability under Stochastic Travel Times. IEEE Transactions on Intelligent Transportation Systems.
- Yang and Zhou (2017). Time-dependent reliable path finding with OTAP/PTT formulations.
