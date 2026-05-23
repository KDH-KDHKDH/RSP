# 复现项目计划 (Plan)

## 目标

用Python复现 Cao et al. (2020) 的ILP精确解法，提供一键运行脚本，支持配置不同路网和参数。

## 目录结构

```
Cao_SOTA_MP/
├── data/
│   ├── generate.py              # 数据生成脚本(独立入口)
│   ├── small/                   # 小规模调试(10节点)
│   ├── full/                    # 65节点完整实验
│   │   ├── seed42/
│   │   ├── seed99/
│   │   └── seed200/
│   └── beijing/                 # 北京路网(待实现)
├── docs/
│   ├── 2020-Cao-SOTA-MP.pdf     # 原始论文
│   ├── paper.html               # 论文精读
│   ├── spec.md                  # 复现规格
│   ├── plan.md                  # 本文件
│   ├── change.md                # 变更日志
│   └── result/                  # 历史报告(按序号保留)
├── configs/
│   ├── default.yaml             # 小规模快速验证
│   └── artificial_n500.yaml     # 65节点N=500(--data-dir切换seed)
├── results/                     # 最近一次运行输出
├── src/                         # 源码(扁平)
│   ├── __init__.py
│   ├── graph.py                 # 路网 + 关联矩阵 + save/load
│   ├── generator.py             # 数据生成 + deadline计算
│   ├── ilp_solver.py            # ILP精确解(核心)
│   ├── milp_solver.py           # MILP近似解
│   ├── dijkstra_solver.py       # Dijkstra基线
│   ├── experiment.py            # 实验编排(加载数据+求解)
│   └── visualize.py             # 画图
├── tests/
│   └── test_solvers.py          # 10个测试
├── run.py                       # 唯一实验入口
└── todo.md                      # 当前待办
```

## 工作流程

```bash
# Step 1: 生成数据
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 99
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 200

# Step 2: 跑实验(--data-dir 切换不同seed)
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed99 --plot
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed200 --plot
```

## 阶段划分

### Phase 1: 基础设施 ✅
- [x] 项目初始化、虚拟环境(RSP级别共享)
- [x] 依赖安装
- [x] 论文精读、规格文档

### Phase 2: 核心实现 ✅
- [x] graph.py / generator.py / ilp_solver.py / milp_solver.py / dijkstra_solver.py
- [x] 10/10单元测试通过
- [x] run.py一键入口

### Phase 3: 65节点实验 ✅
- [x] 枚举优化: 用ILP作为ground-truth(已证明精确)
- [x] N=100实验: ILP 100%, MILP 97.3%, Dijkstra 96.5%
- [x] 结果报告: `docs/result/01_initial_65node.html`

### Phase 4: 求解器升级与N=500实验 ✅
- [x] 安装HiGHS求解器(比CBC快4.8倍)
- [x] N=500实验(seed=42): ILP 100%, MILP 98.0%, Dijkstra 97.1%
- [x] 结果报告: `docs/result/02_n500_solver_compare.html`
- [x] HiGHS 发现内存崩溃 bug，迁移到 SCIP (pyscipopt 6.2.1)
- [x] SCIP 种子42实验完成: ILP 100%, MILP 97.8%, Dijkstra 96.9%
- [x] 报告: `docs/result/03_audit_seed42.html` (取代了之前的03_scip_seed42.html)

### Phase 4b: 审计 + 数据修复 ← 当前
- [x] 数据生成与算法分离(data/generate.py)
- [x] data按 small / full/seed* / beijing 组织
- [x] run.py 新增 --data-dir，保持唯一入口
- [x] 生成3个full数据集(seed=42/99/200)
- [x] 种子42实验完成 (SCIP)
- [x] 全面审计：发现数据方差过低 (CV 中位数 0.25)，导致准确率偏离论文 18-37pp
- [x] 审计报告: `docs/result/03_audit_seed42.html`
- [x] **修复**: generator.py 方差参数 0.1-0.4 → 0.3-0.8, CV中位数 0.25 → 0.54
- [x] 种子42最终实验: ILP 100%, Dijkstra 83.5%, MILP 73.8%
- [x] 种子42分析报告: `docs/result/04_seed42_final.html`
- [x] 准确率指标修复: 概率匹配 → 路径向量匹配 (_path_match)
- [x] **二次修复**: generator.py 方差参数 0.3-0.8 → 0.5-1.2, CV中位数 0.54 → 0.83
- [x] 3个数据集重新生成 (新高方差)
- [ ] 种子42实验 (新高方差数据)
- [ ] 种子99实验
- [ ] 种子200实验
- [ ] 各seed结果分析 + 总体对比
- [ ] 结果报告: `docs/result/06_multi_seed_compare.html`

### Phase 5: 可视化优化
- [ ] 复现Fig.2(a): 准确率 vs α 折线图
- [ ] 复现Fig.2(b)(c): ILP vs 其他方法准时概率散点图
- [ ] 复现Table I: 计算时间对比表

### Phase 6: 北京路网(可选)
- [ ] 获取T-Drive数据集或用OSM+模拟替代
- [ ] 362节点/528边路网构建
- [ ] 实验运行和结果对比

## 报告命名规则

`docs/result/` 下按序号命名，保留历史：
- `01_initial_65node.html` — 首次65节点实验(N=100, CBC)
- `02_n500_solver_compare.html` — N=500实验 + 求解器对比(HiGHS)
- `03_audit_seed42.html` — 项目审计：发现数据方差问题 + 根因分析
- `04_seed42_final.html` — 种子42最终实验 (CV=0.54, 路径匹配修复后)
- `05_project_status.html` — 项目状态全面评估 (2026-05-23)
- `06_multi_seed_compare.html` — 多种子(42/99/200)总体对比 (待完成)

## 关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Ground-truth | ILP本身 | 论文已证明ILP=精确解 |
| 求解器 | PuLP + SCIP (pyscipopt 6.2.1) | 开源高性能，比CBC快2.7倍，稳定可靠(HiGHS有内存bug) |
| 数据流 | 生成与求解分离 | 可预检查图性质，隔离问题 |
| 多seed | 42/99/200 | 验证结果对图拓扑的敏感性 |
