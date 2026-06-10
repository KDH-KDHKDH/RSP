# RSP: Reliable Shortest Path

Reproduction of **Cao et al. (2020)** — an ILP-based exact solver for finding the path
with maximum probability of arriving on-time under stochastic edge travel times.

## Quick Start

```bash
# Install dependencies
uv sync

# Generate experiment data
uv run python Cao_SOTA_MP/data/generate.py --preset small
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42
uv run python Cao_SOTA_MP/data/generate.py --preset beijing
uv run python Cao_SOTA_MP/data/generate.py --preset beijing-conflict

# Run experiment
uv run python Cao_SOTA_MP/run.py
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/beijing.yaml --data-dir Cao_SOTA_MP/data/beijing_conflict --plot

# Run tests
uv run pytest Cao_SOTA_MP/tests/ -v
```

## Project Structure

```
Cao_SOTA_MP/
├── src/                       # 核心求解器
│   ├── graph.py               #   RoadNetwork 数据结构
│   ├── generator.py           #   路网生成、deadline 计算
│   ├── ilp_solver.py          #   ILP 精确求解器
│   ├── milp_solver.py         #   MILP ℓ₁ 松弛求解器
│   ├── dijkstra_solver.py     #   Dijkstra 基线求解器
│   ├── experiment.py          #   实验编排
│   ├── visualize.py           #   可视化
│   └── osm_network.py         #   OSM 路网加载
├── data/                      # 预生成数据集
│   ├── generate.py            #   数据生成入口
│   ├── small/                 #   10 节点快速调试
│   ├── full/seed42/           #   65 节点人工路网
│   ├── full/seed524/          #   65 节点冲突图
│   ├── beijing/               #   587 节点北京 OSM
│   └── beijing_conflict/      #   587 节点多级冲突方差
├── configs/                   # YAML 实验配置
├── tests/                     # 单元测试
└── run.py                     # CLI 入口
```

## Solvers

| Solver | File | Description |
|--------|------|-------------|
| **ILP** | `src/ilp_solver.py` | Exact solution via binary lateness indicators + Big-M constraints |
| **MILP** | `src/milp_solver.py` | L1-norm relaxation with continuous penalty variables |
| **Dijkstra** | `src/dijkstra_solver.py` | Mean shortest path baseline |

All solvers take `(network, W, origin, destination, tau)` and return `{path_x, lateness_count, punctuality_prob, status, solve_time}`.

## Key Results

### Artificial Network (65 nodes, 123 edges, CV=0.83, seed=42)

| Method | Tie-Aware Accuracy | Path-Match Accuracy | Solve Time (mean) |
|--------|--------------------|--------------------|--------------------|
| ILP | **100.0%** | **100.0%** | 0.33s |
| Dijkstra | 88.3% | 75.2% | 0.0003s |
| MILP | 90.2% | 63.7% | 0.17s |

### Beijing OSM Network (587 nodes, 1066 edges, CV=0.775, 3 repeats)

| Method | Tie-Aware Accuracy | Path-Match Accuracy | Solve Time (mean) |
|--------|--------------------|--------------------|--------------------|
| ILP | **100.0%** | **100.0%** | 23.3s |
| Dijkstra | 90.0% | 71.1% | 0.004s |
| MILP | 88.9% | 68.9% | 7.7s |

### Beijing Multi-Level Conflict Variance (587 nodes, 300 jobs)

| Method | Tie-Aware Accuracy | Path-Match Accuracy | Solve Time (mean) |
|--------|--------------------|--------------------|--------------------|
| ILP | **100.0%** | **100.0%** | 18.8s |
| MILP | 84.3% | 58.7% | 6.0s |
| Dijkstra | 67.7% | 49.3% | 0.002s |

ILP = 100% accuracy reproduced. Tie-aware accuracy (`|gap| ≤ 1/N`) is the primary comparison metric; path-match accuracy is retained as a secondary structural diagnostic.

## Key Design Decisions

- **ILP is ground-truth** — no path enumeration needed for accuracy evaluation
- **Data generation is separate from solving** — `data/generate.py` produces self-contained directories
- **SCIP solver** (pyscipopt 6.2.1) — open-source, stable (HiGHS has memory corruption bug)
- **Per-sample tight big-M** — Mᵢ = max(1, ΣⱼW[i,j]-τ), 200-8000× tighter than fixed 1e6
- **Two accuracy metrics**: tie-aware (`|gap| ≤ 1/N`, primary) + path-vector match (auxiliary)
- **SDK boundary** — public API lives under root-level `rsp/`; `Cao_SOTA_MP/src/` remains the core research implementation

## References

- Cao, Z., Guo, H., Zhang, J., Niyato, D., & Fastenrath, U. (2020). Finding the Shortest Path with Maximum Punctuality Probability under Stochastic Travel Times. *IEEE Transactions on Intelligent Transportation Systems*.
