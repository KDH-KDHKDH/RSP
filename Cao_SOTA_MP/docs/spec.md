# 复现规格说明书 (Specification)

## 1. 项目目标

复现 Cao et al. (2020) 的核心算法，提供可配置的一键运行脚本，支持不同路网和参数输入。

## 2. 运行接口规格

### 2.1 数据生成 `data/generate.py`

```bash
uv run python Cao_SOTA_MP/data/generate.py --preset small          # 小规模调试
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42  # 65节点
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 99
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 200
```

输出到 `data/{preset}/` 或 `data/full/seed{N}/`：
- `network.npz` — 图拓扑(边列表 + 节点数)
- `travel_times.npz` — 各repeat的W矩阵
- `od_pairs.npy` — OD对数组
- `meta.yaml` — 生成参数

### 2.2 实验运行 `run.py`

```bash
uv run python run.py                                          # 默认(data/small)
uv run python run.py --data-dir data/full/seed42 --plot       # 指定数据目录
uv run python run.py --config configs/artificial_n500.yaml --data-dir data/full/seed99
```

**参数说明**:
| 参数 | 默认值 | 说明 |
|------|--------|------|
| --config | configs/default.yaml | 配置文件路径 |
| --data-dir | config中data.dir | 预生成数据目录(覆盖config) |
| --plot | false | 是否生成图表 |
| --output | config中output.dir | 输出目录 |

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
  big_m: 1.0e6
  time_limit: 60

output:
  dir: results/
  save_figures: true
  save_csv: true
```

## 3. 核心算法规格

### 2.1 输入规格

| 输入 | 类型 | 描述 |
|------|------|------|
| G = (V, L) | 有向图 | 路网拓扑 |
| W | 矩阵 N×\|L\| | 行程时间样本，Wᵢⱼ为第i个样本在第j条边的行程时间 |
| o, d | 节点ID | 起点、终点 |
| τ | 正实数 | 用户定义的截止时间(deadline) |
| N | 正整数 | 行程时间样本数量 |

### 2.2 输出规格

| 输出 | 类型 | 描述 |
|------|------|------|
| x* | 二值向量 {0,1}^{\|L\|} | 最优路径（边的选择） |
| P* | [0,1] | 最大准时概率 = 1 - (Σιᵢ*/N) |

### 2.3 ILP模型规格（精确解）

**决策变量**:
```
z = [x₁, ..., x_{|L|}, ι₁, ..., ιₙ]  ∈ {0,1}^(|L|+N)
```

**目标函数**:
```
min  Σᵢ₌₁ᴺ ιᵢ
等价于: min f'z, 其中 f = [0,...,0, 1,...,1]
                              |L|个0   N个1
```

**约束条件**:

1. **延迟指示约束** (N个不等式):
```
Σⱼ₌₁^|L| Wᵢⱼ·xⱼ - V·ιᵢ ≤ τ,   ∀i = 1,...,N
```
矩阵形式: Az ≤ B
- A: N×(|L|+N) 矩阵
- A[i, 1:|L|] = [Wᵢ₁, Wᵢ₂, ..., Wᵢ|L|]
- A[i, |L|+i] = -V
- A[i, 其他ι列] = 0
- B = [τ, τ, ..., τ]' (N×1)

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

3. **变量界**:
```
0 ≤ z ≤ 1 (配合整数约束)
z ∈ {0, 1}^(|L|+N)
```

**大M值**: V = 10¹⁰ (或根据数据范围设定足够大的值)

### 2.4 MILP模型规格（近似解，用于对比）

**决策变量**:
```
x ∈ {0,1}^|L|, p ∈ R₊ᴺ
```

**模型**:
```
min  Σᵢ₌₁ᴺ pᵢ
s.t. pᵢ ≥ Σⱼ Wᵢⱼ·xⱼ - τ,  ∀i
     pᵢ ≥ 0,                 ∀i
     Mx = b
     x ∈ {0, 1}^|L|
```

### 2.5 Dijkstra方法规格（基线对比）

- 边权重: 各边行程时间样本的均值 w̄ⱼ = (1/N)Σᵢ Wᵢⱼ
- 求解最短路径（最小期望行程时间路径）

## 3. 实验规格

### 3.1 实验一：人工路网

**路网参数**:
- 节点数: 65
- 边数: 123
- 高连通度有向图

**实验参数**:
- OD对数: 20（随机指定）
- 样本数 N: 500（每条边500个行程时间样本）
- Deadline水平: α ∈ {0.5, 0.6, 0.7, 0.8, 0.9}
- 重复次数: 每组OD+deadline重复10次
- Ground-truth: ILP本身(已证明精确，无需枚举)
- 图种子: seed ∈ {42, 99, 200}（多种子对比图拓扑影响）

**Deadline计算公式**:
```
τ = τ₁ + α·(τ₂ - τ₁)
```
- τ₂: 所有路径中，最小的"最大行程时间"
- τ₁: τ₂对应路径的最短行程时间

**数据生成**:
- 每条边的行程时间随机生成（论文未指定具体分布，合理选择即可）
- 建议: 对每条边使用不同参数的分布（如对数正态、Gamma等）

### 3.2 实验二：北京路网

**路网参数**:
- 节点数: 362
- 边数: 528
- 数据来源: 30000+出租车GPS轨迹（一天）

**实验参数**:
- 与人工路网实验类似
- 行程时间样本来自真实GPS数据处理

**数据获取**:
- 原始数据: T-Drive数据集（微软研究院发布）
- 行程时间估计方法参考 [21] Wang et al., KDD 2014

### 3.3 评估指标

1. **准确率 (Accuracy)**:
```
Accuracy = (找到真实最优路径的次数) / (总测试次数) × 100%
```

2. **准时概率 (Punctuality Probability)**:
```
P(path) = 1 - (迟到样本数 / N)
       = 1 - Card(C(x)) / N
```

3. **计算时间 (Computation Time)**:
- 各方法的平均求解时间（秒）

### 3.4 ILP求解器对比

测试过的开源求解器:
- **SCIP** (当前使用): pyscipopt 6.2.1，比CBC快2.7倍，稳定可靠
- **HiGHS** (已弃用): highspy 1.14.0 存在堆内存损坏bug，特定数据触发崩溃
- **CBC** (备用): 开源稳定，但较慢(avg 2.06s)
- **GLPK**: 开源，较慢

商业替代:
- **CPLEX** (IBM ILOG): 论文使用，有学术许可
- **Gurobi**: 性能接近CPLEX，有学术许可

实现方案: PuLP统一接口，YAML配置切换后端

## 5. 技术栈规格

### 5.1 编程语言
- **Python 3.12+**，虚拟环境在 RSP/ 根目录共享

### 5.2 核心依赖

| 库 | 用途 |
|----|------|
| numpy | 矩阵运算 |
| scipy | 稀疏矩阵、图算法 |
| networkx | 图建模、Dijkstra |
| pulp | ILP/MILP建模(统一接口切换后端) |
| pyscipopt | SCIP求解器(高性能MIP，通过PuLP SCIP_PY调用) |
| matplotlib | 可视化 |
| pandas | 结果汇总 |
| pyyaml | 配置文件解析 |

### 5.3 项目结构

```
Cao_SOTA_MP/
├── docs/                        # 文档(只读参考)
│   ├── 2020-Cao-SOTA-MP.pdf
│   ├── paper.html
│   ├── spec.md
│   ├── plan.md
│   ├── change.md
│   ├── todo.md
│   └── result/                  # 历史报告
├── configs/                     # 实验配置(YAML)
│   ├── default.yaml
│   └── artificial_n500.yaml
├── data/                        # 预生成数据
│   ├── generate.py
│   ├── small/                   # 小规模调试(10节点)
│   └── full/                    # 65节点完整实验
│       ├── seed42/
│       ├── seed99/
│       └── seed200/
├── results/                     # 实验输出
│   └── figures/
├── src/                         # 源码(扁平，不嵌套)
│   ├── __init__.py
│   ├── graph.py                 # 路网 + 关联矩阵 + save/load
│   ├── generator.py             # 数据生成 + deadline计算
│   ├── ilp_solver.py            # ILP精确解
│   ├── milp_solver.py           # MILP近似解
│   ├── dijkstra_solver.py       # Dijkstra基线
│   ├── experiment.py            # 实验编排
│   └── visualize.py             # 画图
├── tests/
│   └── test_solvers.py
├── run.py                       # 唯一实验入口
└── README.md
```

## 6. 验收标准

### 6.1 功能验收
- [ ] `uv run python run.py` 能一键跑通默认配置
- [ ] `--config` 能切换不同路网配置
- [ ] ILP在小规模图上返回正确最优路径(与枚举一致)
- [ ] MILP正确实现ℓ₁范数松弛
- [ ] Dijkstra正确计算最短期望路径

### 6.2 性能验收（对标论文）
- [x] 人工路网: ILP准确率 = 100% (已验证)
- [x] 人工路网: ILP计算时间 ~0.5s (SCIP均值, 最大值~15s)
- [ ] MILP准确率 ∈ [70%, 80%] (当前~74%, CV=0.54; 新高方差下预期更低)
- [ ] Dijkstra准确率 ∈ [60%, 70%] (当前~84%, CV=0.54; 新高方差(CV=0.83)下预期接近论文)

### 6.3 可视化验收
- [ ] 复现Fig.2(a): 准确率 vs deadline
- [ ] 复现Fig.2(b)(c): 准时概率对比散点图
- [ ] 复现Table I: 计算时间对比表
