# 复现规格说明书 (Specification)

## 1. 项目目标

复现 Cao et al. (2020) 的核心算法，提供可配置的一键运行脚本，支持不同路网和参数输入。

## 2. 运行接口规格

### 2.1 数据生成 `data/generate.py`

```bash
uv run python Cao_SOTA_MP/data/generate.py --preset small          # 小规模调试
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42  # 65节点人工路网
uv run python Cao_SOTA_MP/data/generate.py --preset beijing         # 北京OSM路网
```

输出到 `data/{preset}/` 或 `data/full/seed{N}/`：
- `network.npz` — 图拓扑(边列表 + 节点数 + 边属性)
- `travel_times.npz` — 各repeat的W矩阵
- `od_pairs.npy` — OD对数组
- `meta.yaml` — 生成参数

### 2.2 实验运行 `run.py`

```bash
uv run python Cao_SOTA_MP/run.py                                          # 默认(data/small)
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/beijing.yaml --data-dir Cao_SOTA_MP/data/beijing --plot
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| --config | configs/default.yaml | 配置文件路径 |
| --data-dir | config中data.dir | 预生成数据目录(覆盖config) |
| --plot | false | 是否生成图表 |
| --output | config中output.dir | 输出目录 |

### 2.2a Notebook 入口 `experiment.ipynb`

`Cao_SOTA_MP/experiment.ipynb` 是当前推荐的交互式运行入口。

用途：
- 单个 `(repeat, OD, alpha)` case 调试
- 小规模图上的 exact deadline 审计
- 批量实验前的配置确认与结果抽样检查

要求：
- 使用 `uv` 管理的解释器环境
- Notebook 配置区应与 `run.py` / `experiment.py` 的关键协议开关保持一致
- 批量实验 cell 优先复用 `run_experiment()`，避免与主实现漂移

### 2.3 配置文件格式 (YAML)

```yaml
data:
  dir: data/full/seed42     # 数据目录(可被--data-dir覆盖)
  num_samples: 500

experiment:
  num_repeats: 10
  alphas: [0.5, 0.6, 0.7, 0.8, 0.9]

solver:
  backend: SCIP              # CBC / SCIP / GLPK (SCIP recommended)
  big_m: 1000000             # big-M cap (per-sample tight M is bounded by this)
  time_limit: 60

output:
  dir: results/
  save_figures: true
  save_csv: true

candidate_paths:
  max_paths: 1000

deadline:
  mode: heuristic          # heuristic / exact
  enumeration_cutoff: 15   # only used when mode=exact
```

### 2.4 求解器统一接口

```python
def solve_xxx(network: RoadNetwork, W: np.ndarray,
              origin: int, destination: int, tau: float, ...) -> dict:
    return {
        "path_x": np.ndarray,        # binary edge selection vector (|L|,)
        "lateness_count": int,       # number of late samples
        "punctuality_prob": float,   # 1 - lateness_count/N
        "status": str,               # "Optimal" / "NoPath" / "SolverError: ..."
        "solve_time": float,         # seconds
    }
```

## 3. 核心算法规格

### 3.1 输入规格

| 输入 | 类型 | 描述 |
|------|------|------|
| G = (V, L) | 有向图 | 路网拓扑 |
| W | 矩阵 N×\|L\| | 行程时间样本，Wᵢⱼ为第i个样本在第j条边的行程时间 |
| o, d | 节点ID | 起点、终点 |
| τ | 正实数 | 用户定义的截止时间(deadline) |
| N | 正整数 | 行程时间样本数量 |

### 3.2 输出规格

| 输出 | 类型 | 描述 |
|------|------|------|
| x* | 二值向量 {0,1}^{\|L\|} | 最优路径（边的选择） |
| P* | [0,1] | 最大准时概率 = 1 - (Σιᵢ*/N) |

### 3.3 ILP模型规格（精确解）

**决策变量:**
```
z = [x₁, ..., x_{|L|}, ι₁, ..., ιₙ]  ∈ {0,1}^(|L|+N)
```

**目标函数:**
```
min  Σᵢ₌₁ᴺ ιᵢ
等价于: min f'z, 其中 f = [0,...,0, 1,...,1]
                              |L|个0   N个1
```

**约束条件:**

1. **延迟指示约束** (N个不等式):
```
Σⱼ₌₁^|L| Wᵢⱼ·xⱼ - Mᵢ·ιᵢ ≤ τ,   ∀i = 1,...,N
```
- Mᵢ = min(big_m, max(1.0, ΣⱼW[i,j] - τ)) — 逐样本紧界，比固定大M紧200-8000×

2. **流守恒约束** (|V|个等式):
```
Mx = b
```
- M: |V|×|L| 节点-弧关联矩阵
  - M[v,l] = +1 若边l从节点v出发
  - M[v,l] = -1 若边l到达节点v
  - M[v,l] = 0 否则
- b: |V|×1 OD向量
  - b[o] = +1 (起点)
  - b[d] = -1 (终点)
  - b[其他] = 0

3. **变量域:**
```
xⱼ ∈ {0,1},  ιᵢ ∈ {0,1}
```

### 3.4 MILP模型规格（ℓ₁松弛，用于对比）

**决策变量:**
```
x ∈ {0,1}^|L|, p ∈ R₊ᴺ
```

**模型:**
```
min  Σᵢ₌₁ᴺ pᵢ
s.t. pᵢ ≥ Σⱼ Wᵢⱼ·xⱼ - τ,  ∀i
     pᵢ ≥ 0,                 ∀i
     Mx = b
     x ∈ {0, 1}^|L|
```

**注意:** MILP 优化 ℓ₁ 延迟和 (Σpᵢ)，不是准时概率。目标函数不同是MILP准确率低于ILP的根本原因。

### 3.5 Dijkstra方法规格（基线对比）

- 边权重: 各边行程时间样本的均值 w̄ⱼ = (1/N)Σᵢ Wᵢⱼ
- 求解最短路径（最小期望行程时间路径）
- Post-hoc 评估: 用 W @ x 计算该路径的实际准时概率

## 4. 实验规格

### 4.1 实验一：人工路网

**路网参数:**
- 节点数: 65, 边数: 123, 高连通度有向图
- 生成: 随机生成树 + 随机加边, seed=42

**实验参数:**
- OD对数: 20（随机指定，确保连通）
- 样本数 N: 500
- Deadline水平: α ∈ {0.5, 0.6, 0.7, 0.8, 0.9}
- 重复次数: 10
- Ground-truth: ILP本身（论文已证明精确）
- 总任务量: 10 repeats × 20 OD × 5 α = 1000 jobs

**行程时间分布:**
- 对数正态, 每条边独立
- mean ~ Uniform(10, 100) 分钟
- std/mean ~ Uniform(0.5, 1.2) → CV中位数 ≈ 0.83

**Deadline计算公式:**
```
τ = T_min + α·(T_max - T_min)
```
- T_max: 候选路径中的 minimax 路径时间 (min over paths of max sample time)
- T_min: 该 minimax 路径的最短样本时间
- 候选路径池: 4源 (mean SP, worst-case SP, per-sample SP, K-shortest), max 1000

### 4.2 实验二：北京路网

**路网参数:**
- 节点数: 587, 边数: 1066
- 数据来源: OpenStreetMap (PBF离线提取, bbbike.org)
- 区域: 39.89-39.94N, 116.37-116.42E (~5km × 5km)
- 道路等级: 次要道路及以上 (secondary+)

**实验参数:**
- 重复: 3次 (因网络规模大)
- 样本数 N: 500
- OD对: 10
- Deadline水平: α ∈ {0.5, 0.7, 0.9}
- 总任务量: 3 repeats × 10 OD × 3 α = 90 jobs

**行程时间分布:**
- 对数正态, 参数由路段 OSM 属性决定
- mean = 路段长度 / 速度 (按道路等级: 高速60km/h, 主干道50km/h, 次干道40km/h, 小路30km/h)
- CV范围按道路类型:
  - 主干道 (trunk/primary): 0.5-0.8
  - 次干道 (secondary): 0.7-1.1
  - 小路 (tertiary/residential): 0.9-1.3
- CV中位数 ≈ 0.775

**方案选择:**
- 方案 C: OSM 真实拓扑 + 属性驱动模拟行程时间
- 原因: 拓扑真实, 参数有物理含义, 可复现
- 注: osmnx Overpass API 不可用 (GFW), 改用 osmium 离线解析 PBF

**后续扩展方向（计划中）:**
- 在北京真实拓扑上引入“冲突化方差”方案，使部分走廊呈现“快但险”，另一部分呈现“慢但稳”
- 该扩展应优先依赖道路属性分层，而不是全图统一抬高 CV
- 扩展实验的目标不是单纯增加方差，而是制造可替代路径之间的均值-风险冲突

### 4.3 评估指标

1. **Tie-Aware 准确率（主准确率）:**
   - `tie_aware_correct = |p_ILP - p_method| ≤ 1/N`
   - 含义：若两条路径的准时概率差异不超过一个样本分辨率，则视为实践上等效
   - 当前默认主比较口径使用该指标

2. **路径匹配准确率 (Path-Match Accuracy, 次级指标):**
   - `correct = np.array_equal(method_path, ilp_path)`
   - 含义：严格比较边选择向量是否完全一致
   - 用途：保留作结构诊断，不作为唯一主结论来源

3. **Objective Gap:**
   - `objective_gap = p_ILP - p_method`
   - 准时概率差距的量化指标

4. **计算时间:** 各方法的平均求解时间（秒）

5. **辅助指标:** late_count, delay_sum, max_delay, path_length, mean_time
6. **求解状态指标:** `status`, `reference_available`

### 4.4 Deadline 协议

论文定义：
```
τ = τ1 + α·(τ2 - τ1)
```
- `τ2`: 所有候选路径中的 minimax path time，即 `min_P max_i T_i(P)`
- `τ1`: 达到 `τ2` 的同一路径上的最短样本时间

本项目支持两种模式：
- `deadline.mode = heuristic`：使用候选路径池近似 `τ2`
- `deadline.mode = exact`：在可枚举的小图上直接枚举所有简单路径，严格按论文定义计算

要求：
- 小图审计、单元测试、论文协议验证时优先使用 `exact`
- 大图批量实验默认使用 `heuristic`

### 4.5 Tie-Aware 容忍规则

**主规则 (|gap| ≤ 1/N):**
```
tie_aware_correct = |p_ILP - p_method| ≤ 1/N
```
- `1/N` 对应一个样本的概率分辨率
- 与现有历史报告连续，便于横向比较
- 作为默认主准确率指标

**明确不建议:**
- 没有统计依据地“随便缩一点余量”
- 引入复杂的 per-OD 自适应阈值规则作为默认方案

**当前维护决定:**
- 默认与主报告口径固定使用 `|gap| ≤ 1/N`
- 不再继续扩展复杂阈值分支

### 4.6 后续人工图实验要求

新增冲突型人工图实验时，应满足：
- 不覆盖当前 `seed42` 结果，作为独立实验族保存
- 推荐 seed: `524`
- 两类边参数：
  - `fast_risky`: `mean ~ Uniform(10, 50)`, `cv ~ Uniform(0.8, 1.4)`
  - `slow_stable`: `mean ~ Uniform(40, 90)`, `cv ~ Uniform(0.2, 0.6)`
- 需要单独检查新图是否真的带来“快但险 vs 慢但稳”的路径冲突，而不只是整体 CV 变化

### 4.7 后续北京冲突化方差方案要求

北京数据集如果要做“类似 conflict graph”的扩展，建议满足：
- 基于真实道路属性做分层，而不是完全随机分边
- 至少区分两类走廊：
  - 快但险：较低均值、较高 CV
  - 慢但稳：较高均值、较低 CV
- 先证明“存在路径级冲突”，再解读求解器排名变化
- 必须额外输出以下审计项：
  - 冲突 OD 占比
  - 每种方法最终选路中两类边的占比
  - 冲突 OD 与非冲突 OD 的分开结果

## 5. 求解器规格

| 求解器 | 状态 | 说明 |
|--------|------|------|
| **SCIP** (pyscipopt 6.2.1) | 当前使用 | 开源高性能，比CBC快2.7倍，稳定可靠 |
| HiGHS (highspy 1.14.0) | 已弃用 | 堆内存损坏bug (double free)，特定数据触发崩溃 |
| CBC | 备用 | 开源稳定，但较慢 (avg 2.06s) |
| GLPK | 备用 | 开源，较慢 |

商业替代: CPLEX (论文使用), Gurobi。实现方案: PuLP统一接口，YAML配置切换后端。

## 6. 验收标准

### 6.1 功能验收
- [x] `uv run python run.py` 能一键跑通默认配置
- [x] `--config` 能切换不同路网配置
- [x] Notebook 配置区与 `run.py` 的 deadline / 审计开关保持一致
- [x] ILP在小规模图上返回正确最优路径(与枚举一致, test_ilp_returns_optimal通过)
- [x] MILP正确实现ℓ₁范数松弛
- [x] Dijkstra正确计算最短期望路径
- [x] `status != Optimal` 的 ILP job 在结果中保留记录，不得静默跳过

### 6.2 性能验收（对标论文）

**人工路网 (CV=0.83, seed=42):**
- [x] ILP准确率 = 100% (已验证)
- [x] ILP计算时间 ~0.34s (与论文CPLEX 0.32s持平)
- [x] tie-aware准确率达到 >85% (Dijkstra 88.3%, MILP 90.2%)
- [x] 路径匹配准确率保留作辅助诊断 (Dijkstra 75.2%, MILP 63.7%)

**北京路网 (CV=0.775, 报告 12):**
- [x] ILP准确率 = 100%
- [x] ILP平均计算时间 23.3s，单例可触及 120s time limit 但能返回 Optimal
- [x] Dijkstra tie-aware = 90.0%，MILP tie-aware = 88.9%
- [x] 路径匹配准确率保留作辅助诊断 (Dijkstra 71.1%, MILP 68.9%)

### 6.3 可视化验收
- [ ] 主图切换为 Tie-Aware Accuracy vs α
- [ ] 路径匹配准确率图保留为附图/次级图
- [x] 复现 Fig.2(b)(c): 准时概率对比散点图
- [x] 复现 Table I: 计算时间对比表

### 6.4 测试验收
- [x] 14/14 单元测试通过
- [x] 覆盖: 图操作 + 关联矩阵 + ILP最优性(枚举验证) + 求解器接口 + deadline exact mode + 非最优样本记账
