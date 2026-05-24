# 复现项目计划 (Plan)

## 目标

用Python复现 Cao et al. (2020) 的ILP精确解法，提供一键运行脚本，支持配置不同路网和参数。

## 当前状态

Phase 1-9 全部完成。ILP=100% 精确解已复现。10/10测试通过。两个路网验证完成（人工65节点 + 北京587节点）。

**待推进:** 评估口径切换（tie-aware 主准确率）、多 seed 统计显著性实验与真实轨迹扩展。论文协议对齐和 notebook-first 入口已落地。

## 工作流程

```bash
# Step 0: 优先使用 Notebook 入口
# 在 VS Code / Jupyter 中打开:
#   Cao_SOTA_MP/experiment.ipynb
#
# Notebook 用于:
# - 单个 case 调试
# - 小规模 exact deadline 审计
# - 批量实验的交互式运行
#
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

### Phase 5: 可视化优化 ✅
- [x] 复现 Fig.2(a): 准确率 vs α 折线图
- [x] 复现 Fig.2(b)(c): ILP vs 其他方法准时概率散点图
- [x] 输出 Table I 风格计算时间汇总表 (`compute_time_summary.csv`)

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

### Phase 9: 北京高方差实验 ✅
- [x] 北京高方差实验完成 (CV=0.775, 90 jobs, 约 140 min)
- [x] 生成报告 12，记录北京高方差阶段的最新结果

### Maintenance: 审计对齐与后续排程
- [x] 对齐 README / plan / todo / spec 与 report 12 后状态
- [x] 北京 `meta.yaml` 补充 `highway_cv_range`
- [x] 新增维护跟进报告，解释历史报告不可变与报告关系
- [x] Candidate path / deadline 逻辑补单元测试
- [x] PuLP 4.0 warning workaround，消除 deprecation warning

### Protocol Alignment: 论文协议对齐
- [x] `deadline.mode`：支持 `heuristic` / `exact`，小图审计时按论文定义枚举路径计算 τ
- [x] ILP 非最优样本不再 `skip`，而是完整记录 `status` / `reference_available`
- [x] Notebook 作为优先运行入口，配置项覆盖上述协议开关，并复用 `run_experiment()`

### Expansion
- [ ] 评估口径切换：以 tie-aware accuracy 作为主准确率，path-match 降为辅助诊断
- [ ] 图表切换：accuracy 曲线和总表默认展示 tie-aware accuracy，path-match 作为附图/附表
- [ ] tie-aware 阈值敏感性分析：保留 `|gap| ≤ 1/N` 作为主标准，补充一个统一更严格阈值（如 `0.5/N`）对比
- [ ] 多 seed 统计显著性实验
- [ ] 真实轨迹数据接入（如 T-Drive）

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
| 09 | `09_seed42_audit_fix.html` | 人工路网 Phase 8 审计修复后的最新结果 (新指标系统) |
| 10 | `10_beijing_audit_fix.html` | 北京路网 Phase 8 审计修复后的最新结果 (旧CV, 新指标系统) |
| 11 | `11_project_audit.html` | 项目全面审计报告 |
| 12 | `12_beijing_highvar.html` | 北京路网高方差阶段的最新结果 (CV=0.775) |
| 13 | `13_maintenance_followup.html` | 维护/审计对齐报告 + 后续任务排程 |
| 14 | `14_deadline_protocol_audit.html` | small 数据集协议审计：heuristic 与 exact deadline 对照 |
| 15 | `15_full_seed42_notebook_rerun.html` | full/seed42 在 notebook + SCIP 下的正式实验报告 |
| 16 | `16_full_seed42_detailed_review.html` | full/seed42 详细指标分析、计划与项目状态审计 |

## 关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Ground-truth | ILP本身 | 论文已证明ILP=精确解 |
| 求解器 | PuLP + SCIP (pyscipopt 6.2.1) | 开源高性能，比CBC快2.7倍，稳定可靠 (HiGHS有内存bug) |
| big-M | 逐样本紧界 Mᵢ = max(1, ΣⱼW[i,j]-τ) | 比固定1e6紧200-8000×, LP relaxation更紧 |
| 数据流 | 生成与求解分离 | 可预检查图性质，隔离问题 |
| 接口设计 | --data-dir / --seed | 保留多seed扩展能力，当前聚焦单seed |
| 北京路网 | 方案C: OSM拓扑 + 属性驱动模拟 | 拓扑真实, 参数有物理含义, 可复现 |
| 评估指标 | tie-aware 为主 + 路径匹配为辅 | tie-aware更接近“概率上是否等价”的问题；path-match保留作结构诊断 |
