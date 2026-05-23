# 复现项目计划 (Plan)

## 目标

用Python复现 Cao et al. (2020) 的ILP精确解法，提供一键运行脚本，支持配置不同路网和参数。

## 当前状态

Phase 1-8 全部完成。ILP=100% 精确解已复现。10/10测试通过。两个路网验证完成（人工65节点 + 北京587节点）。

**待推进:** Phase 5 (可视化优化)、Phase 9 (北京高方差实验重跑)。

## 工作流程

```bash
# Step 1: 生成数据
uv run python Cao_SOTA_MP/data/generate.py --preset small
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42
uv run python Cao_SOTA_MP/data/generate.py --preset beijing

# Step 2: 跑实验
uv run python Cao_SOTA_MP/run.py                                          # small (默认)
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/beijing.yaml --data-dir Cao_SOTA_MP/data/beijing --plot
```

## 阶段划分

### Phase 1-2: 基础设施 + 核心实现 ✅
项目初始化，RSP级别共享venv。ILP/MILP/Dijkstra 三个求解器实现，10/10测试通过，YAML配置系统。

### Phase 3: 65节点 N=100 实验 ✅
首次完整实验，ILP 100%精确解验证。用ILP作为ground-truth（论文已证明精确）。

### Phase 4: N=500 + 求解器升级 ✅
HiGHS 发现内存损坏bug后迁移到 SCIP (pyscipopt 6.2.1)。数据生成与求解分离。

### Phase 4b: 方差修复 ✅
两轮方差增大 (CV 0.25 → 0.54 → 0.83)，修复高估准确率问题。准确率指标从概率匹配改为路径向量匹配。项目全面修复(P0-P3)。

### Phase 5: 可视化优化
- [ ] 复现 Fig.2(a): 准确率 vs α 折线图
- [ ] 复现 Fig.2(b)(c): ILP vs 其他方法准时概率散点图
- [ ] 复现 Table I: 计算时间对比表

### Phase 6: 北京路网 ✅
**方案 C:** OSM真实路网拓扑 + 属性驱动模拟行程时间。

- 数据源: bbbike.org PBF (21MB), osmium离线解析（osmnx被GFW阻断）
- 区域: 中心城区 (39.89-39.94N, 116.37-116.42E), 次要道路及以上
- 规模: 587节点, 1066边
- 行程时间: 对数正态, mean = length/speed (30-60 km/h), CV按道路类型 (0.5-1.3)
- 新增 `src/osm_network.py`, `configs/beijing.yaml`, `data/generate.py --preset beijing`

### Phase 7: 求解器优化 ✅
- Tight big-M: 固定1e6 → 逐样本 Mᵢ = max(1, ΣⱼW[i,j]-τ)。人工路网 M 缩小~200×，北京路网~8000×。ILP求解时间均值 -39%，与论文CPLEX 0.32s持平。
- MILP诊断: x确认为Binary，ILP比MILP多500个整数变量（ιᵢ vs pᵢ），时间差异源于模型结构非bug。
- 进度条/ETA显示。

### Phase 8: 审计修复 ✅
- 求解器返回标准化 (lateness_count)
- 候选路径池扩展到4源 (mean SP, worst-case SP, per-sample SP, K-shortest), max 1000
- 新指标: objective_gap, tie_aware_correct, late_count, delay_sum, max_delay, path_length, mean_time
- worst_cases.csv 输出, deadline diagnostics
- 双路网重跑验证 (报告09/10)
- tie_aware_accuracy 纳入主评估指标
- 北京CV增大 (median 0.54→0.775), 数据已生成

### Phase 9: 北京高方差实验
- [ ] 重跑北京实验 (CV=0.775, 数据已生成, 预计 ~140 min)
- [ ] 更新报告 08/10 到新高方差数据

## 报告命名规则

`docs/report/` 下按序号命名，保留历史，文件不可变：

| # | 文件 | 内容 |
|---|------|------|
| — | `index.html` | 报告索引页（一键浏览全部报告） |
| 01 | `01_initial_65node.html` | 首次65节点实验 (N=100, CBC) |
| 02 | `02_n500_solver_compare.html` | N=500实验 + 求解器对比 (HiGHS) |
| 03 | `03_audit_seed42.html` | 项目审计：发现数据方差问题 + 根因分析 |
| 04 | `04_seed42_final.html` | 种子42实验 (CV=0.54, 路径匹配修复后) |
| 05 | `05_project_status.html` | 项目状态全面评估 |
| 06 | `06_seed42_highvar.html` | 种子42高方差实验 (CV=0.83) |
| 07 | `07_seed42_tightM.html` | Tight big-M 优化验证 |
| 08 | `08_beijing.html` | 北京路网实验 |
| 09 | `09_seed42_audit_fix.html` | **权威**: 人工路网 Phase 8 审计修复 (新指标系统) |
| 10 | `10_beijing_audit_fix.html` | **权威**: 北京路网 Phase 8 审计修复 (旧CV, 新指标系统) |
| 11 | `11_project_audit.html` | 项目全面审计报告 |

## 关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Ground-truth | ILP本身 | 论文已证明ILP=精确解 |
| 求解器 | PuLP + SCIP (pyscipopt 6.2.1) | 开源高性能，比CBC快2.7倍，稳定可靠 (HiGHS有内存bug) |
| big-M | 逐样本紧界 Mᵢ = max(1, ΣⱼW[i,j]-τ) | 比固定1e6紧200-8000×, LP relaxation更紧 |
| 数据流 | 生成与求解分离 | 可预检查图性质，隔离问题 |
| 接口设计 | --data-dir / --seed | 保留多seed扩展能力，当前聚焦单seed |
| 北京路网 | 方案C: OSM拓扑 + 属性驱动模拟 | 拓扑真实, 参数有物理含义, 可复现 |
| 评估指标 | 路径匹配 + tie-aware (|gap| ≤ 1/N) | 路径匹配严格但易受采样误差影响, tie-aware更合理 |
