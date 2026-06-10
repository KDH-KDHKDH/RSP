# RSP — Reliable Shortest Path

复现 **Cao et al. (2020)** 的 ILP 精确解法：在有随机边行程时间的有向路网中，找到**准时到达概率最大**的路径。

## 项目结构

```
RSP/
├── rsp/                              # 对外 Python SDK
│   ├── __init__.py                   #   导出 RSPDataset, RSPConfig, RSPRunner, RSPResult
│   ├── dataset.py                    #   RSPDataset — 数据加载/校验
│   ├── config.py                     #   RSPConfig — 实验配置
│   ├── runner.py                     #   RSPRunner — 单 case / 批量运行
│   ├── result.py                     #   RSPResult / RSPCaseResult — 结果读取
│   ├── metrics.py                    #   公共指标 helper
│   └── adapters/cao.py               #   调用核心算法的适配层
│
├── Cao_SOTA_MP/                      # 核心算法与复现资产
│   ├── src/                          #   求解器实现
│   │   ├── graph.py                  #     RoadNetwork 数据结构
│   │   ├── ilp_solver.py             #     ILP 精确求解器
│   │   ├── milp_solver.py            #     MILP ℓ₁ 松弛求解器
│   │   ├── dijkstra_solver.py        #     Dijkstra 基线求解器
│   │   ├── generator.py              #     路网生成、deadline 计算
│   │   ├── experiment.py             #     实验编排
│   │   ├── visualize.py              #     可视化
│   │   └── osm_network.py            #     OSM 路网加载
│   ├── data/generate.py              #   数据生成入口
│   ├── run.py                        #   CLI 入口
│   ├── experiment.ipynb             #   Notebook 入口
│   └── tests/                        #   32 个测试
│
├── configs/                          # SDK 配置模板
└── notebook/mp.ipynb                 # SDK 使用示例
```

## 快速开始

```bash
uv sync
uv run pytest Cao_SOTA_MP/tests/ -v

# 生成数据
uv run python Cao_SOTA_MP/data/generate.py --preset small
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42

# 运行实验
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot
```

## SDK 使用指南

```python
from rsp import RSPDataset, RSPConfig, RSPRunner

# 1. 加载数据
dataset = RSPDataset.from_directory("Cao_SOTA_MP/data/small")

# 2. 配置
config = RSPConfig(
    methods=("ILP",),
    alphas=(0.5, 0.7, 0.9),
    num_repeats=1,
    num_od_pairs=3,
    solver_backend="SCIP",
)

# 3. 运行
runner = RSPRunner(dataset, config)
result = runner.run()

# 4. 读取结果
print(result.summary())          # 方法级汇总
print(result.by_alpha())         # 按 alpha 分组
```

### RSPDataset — 数据容器

```python
# 从预生成目录加载
dataset = RSPDataset.from_directory("Cao_SOTA_MP/data/small")

# 从内存构建
import networkx as nx, numpy as np
G = nx.DiGraph()
G.add_edge(0, 1); G.add_edge(0, 2)
G.add_edge(1, 3); G.add_edge(2, 3)
W = np.random.lognormal(mean=3.0, sigma=0.8, size=(500, 4))
dataset = RSPDataset.from_arrays(G, W, [(0, 3)])
# 自动校验：边列数、OD 节点存在性、可达性
```

### RSPConfig — 实验配置

```python
config = RSPConfig(
    methods=("ILP",),          # ILP | MILP | Dijkstra
    alphas=(0.5, 0.7, 0.9),   # α ∈ [0, 1]
    num_repeats=None,          # None = 用完所有 repeat
    num_od_pairs=None,         # None = 用完所有 OD
    solver_backend="SCIP",     # SCIP / CBC / GLPK
    time_limit=60,
    deadline_mode="heuristic", # heuristic / exact
)
# 也可从 YAML 加载
config = RSPConfig.from_yaml("Cao_SOTA_MP/configs/beijing.yaml")
```

### RSPRunner — 运行实验

```python
runner = RSPRunner(dataset, config)

# 单 case 调试
case = runner.solve_case(repeat=0, od_idx=0, alpha=0.7)
print(case.ilp["punctuality_prob"], case.tau)

# 解码最优路径
edge_idx = [j for j, v in enumerate(case.ilp["path_x"]) if v > 0.5]
path = [dataset.edge_order[j] for j in edge_idx]

# 批量运行
result = runner.run(progress=True)
```

### RSPResult — 读取结果

```python
result.to_dataframe()                    # 原始 DataFrame
result.summary()                         # 方法级汇总（punctuality, accuracy, solve_time）
result.accuracy("tie_aware")             # tie-aware 准确率
result.accuracy("path_match")            # 路径匹配准确率
result.solve_time()                      # 求解时间统计
result.status_counts()                   # solver 状态分布
result.by_alpha()                        # 按 alpha 分组
result.by_od()                           # 按 OD 对分组
result.method_comparison(reference="ILP")
result.save_csv("results.csv")
result.save_figures("figures/")
```

## 求解器

| 求解器 | 文件 | 角色 |
|--------|------|------|
| ILP | `src/ilp_solver.py` | 精确解（ground-truth） |
| MILP | `src/milp_solver.py` | ℓ₁ 松弛近似 |
| Dijkstra | `src/dijkstra_solver.py` | 均值最短路径基线 |

统一返回：`{path_x, punctuality_prob, lateness_count, status, solve_time}`。
