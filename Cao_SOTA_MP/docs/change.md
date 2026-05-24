# 变更日志 (Changelog)

## [2026-05-24] 报告 19: 冲突图实验完成 — MILP ℓ₁ 松弛在双峰边类型图上优势显著

- **实验完成**: seed524 冲突图 1000 jobs, ILP 100% Optimal, 全部求解成功
- **MILP tie-aware 91.2%** (vs Dijkstra 87.3%), MILP 在 tie-aware 指标上持续领先
- **MILP 路径匹配准确率跃升 +11.6pp** (63.7% → 75.3%) — 双峰风险结构使 ℓ₁ 松弛更频繁恢复 ILP 最优路径
- **Dijkstra 路径匹配优势大幅缩小**: 从 +11.5pp 降至 +2.9pp
- **冲突图创造了更难实例**: α=0.5 时 ILP 最低准时率 63.2% (vs seed42 的 76.8%)
- **ILP 求解时间下降 36%** (0.37s → 0.24s) — 结构化的冲突图使分支定界更高效
- **MILP ≥ Dijkstra 在 93.9% 的 job 上** — MILP 在冲突图中全面占优
- 报告索引更新至 19 份

## [2026-05-24] Conflict Graph: 数据生成 + 结构审计 + strict 代码清理

- **Strict threshold cleanup**: 从 `experiment.py` / `visualize.py` / `experiment.ipynb` 移除所有 `tie_aware_correct_strict` (0.5/N) 代码和图表。14 个测试通过。
- **Dual edge type graph (seed 524)**: 
  - `src/generator.py`: 新增 `assign_conflict_edge_types()` (一次性分配边类型) 和 `generate_conflict_travel_times()` (基于预设边类型生成对数正态旅行时间)
  - `src/graph.py`: `save()`/`load()` 支持 `edge_type` 序列化 (code+name 编码)
  - `data/generate.py`: 新增 `--preset conflict` (65 节点, 123 边, 500 样本, 10 重复)
- **Conflict audit results**: 61 fast_risky (CV 0.76-1.84, mean 10-49), 62 slow_stable (CV 0.20-0.64, mean 39-89)。CV 无重叠，11/20 OD 对有冲突型路径。
- `experiment.ipynb` 配置更新：DATA_DIR = `data/full/seed524`, OUTPUT_DIR = `results/conflict_seed524_scip/`
- 待用户运行 notebook 后进行结果审计并生成报告 19

## [2026-05-24] 报告 18: Metric Policy 审计与阈值敏感性结论
- 基于 full/seed42 + SCIP 的 Metric Policy 变更后重跑完成 (1000 jobs, ILP 100% Optimal)
- 主准确率 (tie-aware, |gap| ≤ 1/N): MILP 90.2%, Dijkstra 88.3%
- 严格阈值 (|gap| ≤ 0.5/N): 与主阈值完全一致——因准时概率差为 1/N 整数倍，gap 不可能落在 (0.5/N, 1/N) 内
- 结论：0.5/N 严格阈值在 N=500 下无增量信息，保留为代码中的可选诊断开关，不作为常规指标
- 修复 experiment.py 中 MILP/Dijkstra 行缺少 `tie_aware_correct_strict` 字段的 bug
- 结果与报告 09/15/16/17 完全一致，验证 seeded generation 确定性
- 报告索引更新至 18 份

## [2026-05-24] Metric Policy 实现：主准确率切换 + 阈值敏感性
- **主准确率切换**: `print_summary()` / `plot_accuracy_vs_deadline()` / `save_compute_time_table()` 默认展示 tie-aware accuracy 作为主指标，path-match 降为辅助
- **阈值敏感性**: `run_experiment()` 新增 `tie_aware_correct_strict` 列 (`|gap| ≤ 0.5/N`)，与默认 `1/N` 阈值并列输出
- `accuracy_vs_deadline.png` 现为主 tie-aware 图表，新增 `tie_aware_strict_accuracy_vs_deadline.png` 和 `path_match_accuracy_vs_deadline.png`
- Notebook `experiment.ipynb` 所有表格/图表同步切换，新增严格阈值对比
- README 结果表列顺序调整 (Tie-Aware 在前)，spec.md 文档化双阈值规则
- plan.md / todo.md 标记 metric policy 三项任务完成

## [2026-05-24] 维护文档更新：冲突图机制与北京方差方案
- `plan.md` / `todo.md` / `spec.md` 新增冲突图机制证据补强任务：冲突 OD / 非冲突 OD 拆分、边类型占比、MILP 提升来源分析
- 新增北京冲突化方差方案规划：在真实拓扑上设计“快但险 vs 慢但稳”的属性分层，并先定义审计标准
- 维护文档同步到报告 19 当前状态，补齐报告数和最新实验族信息

## [2026-05-24] 维护文档更新：主准确率、固定阈值与新人工图方向
- README / plan / todo / spec / handover 同步记录后续评估口径：将 tie-aware accuracy 作为主准确率，路径匹配降为辅助结构诊断
- 明确当前默认容忍规则继续使用 `|gap| ≤ 1/N`
- 明确“直接随意缩小一点余量”不作为默认方案；阈值策略保持简单，不再继续复杂化
- 将后续待办收敛为：清理 strict 代码与产物、新人工图实验族、真实轨迹扩展

## [2026-05-24] Full Seed42 详细复盘报告 16
- 基于 `results/full_protocol_seed42_scip/` 的 notebook rerun 输出，新增详细复盘报告 `docs/report/16_full_seed42_detailed_review.html`
- 报告 16 包含：总体指标、按 α 分析、repeat 稳定性、objective gap 结构、worst cases、后续计划和项目状态简单审计
- 报告索引更新到 16 份

## [2026-05-24] Full Seed42 Notebook Rerun + 报告 15
- 基于 `experiment.ipynb` 当前输出结果，整理 full/seed42 + SCIP 的正式实验报告 `docs/report/15_full_seed42_notebook_rerun.html`
- 补写结构化结果文件：`summary.csv`、`status_counts.csv`、`path_match_by_alpha.csv`、`tie_aware_by_alpha.csv`
- 结果确认：ILP 100%, Dijkstra 75.2%, MILP 63.7%，ILP reference availability = 100%
- 说明计时口径变化：当前报告使用 wall-clock solve time，不再直接依赖 solver 内部时间字段

## [2026-05-24] Deadline 协议审计实验
- 使用 notebook-first 共享逻辑跑 `data/small` 的 `deadline.mode=heuristic` vs `exact` 对照实验（45 jobs）
- 结果：`tau_diff` 在 45/45 个 job 上均为 0，Dijkstra / MILP / ILP 的 path-match、tie-aware 和 punctuality 结果完全一致
- 新增报告 14: `docs/report/14_deadline_protocol_audit.html`
- 结果落盘到 `results/protocol_audit_small/`
- 发现并修复 CBC 下 `prob.solutionTime` 可能为负的问题，ILP/MILP 改为统一返回 wall-clock solve time

## [2026-05-24] 维护对齐 + 元数据追溯修复
- README / plan / todo / spec 对齐到 report 12 之后的真实状态，移除“北京高方差待跑”的过时表述
- Beijing 数据生成元数据补全：`data/generate.py` 现在写入 `highway_cv_range`，`data/beijing/meta.yaml` 已同步补齐
- `network_source` 统一为离线 GraphML/PBF 提取表述，避免与文档中的 `osmium` 离线流程冲突
- 新增报告 13: `docs/report/13_maintenance_followup.html`，用于承接 report 11 中已被后续结果更新的维护/审计结论
- 报告索引与 handover 更新，明确 report 09 / 12 为当前结果；report 07 的 MILP 抽样偏差改由后续维护报告说明，不覆写历史编号报告
- 论文协议对齐：`deadline.mode` 支持 `heuristic / exact`，小图审计可按论文定义直接枚举路径计算 τ
- 实验记账修复：`run_experiment()` 不再静默跳过 `ILP != Optimal` 的 job，而是保留 `status` / `reference_available` / `reference_status`
- Notebook-first：`notebooks/experiment.ipynb` 变为推荐运行入口，并复用 `run_experiment()` 共享主实验逻辑
- 测试继续扩展到 14 项，覆盖 exact deadline 和非最优样本保留

## [2026-05-24] 北京高方差实验完成 + Notebook + 索引更新
- 北京路网高方差实验 (CV=0.775) 完成: ILP 100%, Dijkstra 71.1% (-14.5pp vs CV=0.54), MILP 68.9% (-12.2pp)
- ILP 优势在高方差下显著扩大: vs Dijkstra +28.9pp, vs MILP +31.1pp
- 报告 12 生成: `docs/report/12_beijing_highvar.html`
- 报告索引页更新: 新增 Phase 9 分类, 关键指标演进表加入报告 12
- Jupyter Notebook 创建: `notebooks/experiment.ipynb` (32 cells, 复现 run.py 完整工作流)

## [2026-05-24] 文档规范化
- 明确各文档职责和内容限制 (详见 README.md Documentation Structure)
- CLAUDE.md 新增 Documentation Rules 速查表
- todo.md 从项目根目录移入 docs/
- plan.md: 移除目录结构(重复README), 合并已完成阶段, 新增Phase 9, 报告表改为表格
- spec.md: 修复章节编号(3→4→5→6), 更新验收标准(CV=0.83), 移除项目结构(重复README), 新增求解器统一接口、北京验收标准、测试验收
- change.md: 精简过时条目

## [2026-05-23] 项目全面审计 + 状态报告
- 审计范围: 代码 (1469行) · 数据 (3个数据集) · 结果 (10份报告) · 文档 (5个文件) · 测试 (10/10)
- 代码审计: 所有求解器实现正确，与论文一致。ILP tight big-M, MILP ℓ₁ relaxation, Dijkstra 均值SP 全部验证通过
- 数据: seed42 CV=0.834 ✅, beijing CV=0.775 (新数据, 实验未跑 ⚠️), beijing meta.yaml 缺少 CV 范围记录 ⚠️
- 文档: 与当前状态对齐 ✅, spec.md 验收标准仍引用旧 CV=0.54 数据 (低优先级)
- 报告: docs/report/11_project_audit.html

## [2026-05-23] Phase 8 完成: 审计修复 + 双路网验证
- 求解器返回标准化: MILP/Dijkstra 统一返回 `lateness_count`
- 候选路径池扩展: 4源 (mean SP, worst-case SP, per-sample SP, K-shortest), max 1000, 去重截断
- 新指标: objective_gap, tie_aware_correct, late_count, delay_sum, max_delay, path_length, mean_time
- `_save_worst_cases(df, output_dir)` 输出 MILP < Dijkstra 诊断 → worst_cases.csv
- `compute_deadline` 新增 `return_diagnostics` 参数
- tie_aware_accuracy 纳入主评估指标
- **人工路网重跑 (seed42)**: 1000 jobs, 16.4min。ILP 100%, Dijkstra 75.2%, MILP 63.7%。tie_aware: MILP 90.2% > Dijkstra 88.3% (反转排名!)。报告 09
- **北京路网重跑**: 90 jobs, 142.7min。ILP 100%, Dijkstra 85.6%, MILP 81.1%。tie_aware: Dijkstra 96.7% ≈ MILP 95.6%。报告 10

## [2026-05-23] Phase 6-7 完成: 北京路网 + 求解器优化
- **北京路网**: 587节点、1066边真实 OSM 路网。方案C: PBF离线提取 + 属性驱动模拟行程时间 (osmnx被GFW阻断)
- 实验: 3 repeats × 10 OD × 3 α = 90 jobs, 51.7min。ILP 100%, Dijkstra 85.6%, MILP 81.1%
  - 意外: MILP落后于Dijkstra (81.1% vs 85.6%), 与人工路网相反
  - ILP 求解 22.5s (人工路网 0.33s, 68×差距), α=0.5是瓶颈 (41.6s)
- **Tight big-M**: 固定1e6 → 逐样本 Mᵢ = max(1, ΣⱼW[i,j]-τ)。ILP时间均值 -39% (0.544s→0.331s), 与论文CPLEX 0.32s持平
- **MILP诊断**: x确认为Binary, ILP比MILP多500个整数变量 (ιᵢ vs pᵢ), 时间差异源于模型结构非bug
- 进度条/ETA + 多线程评估 (SCIP内部并行)
- 报告 07, 08

## [2026-05-23] 高方差种子42实验 (CV=0.83)
- **二次方差增大**: generator.py 方差参数 0.3-0.8 → 0.5-1.2, CV中位数 0.54 → 0.83
- ILP 100%, Dijkstra 75.2%, MILP 63.7% — ILP优势扩大至 +24.8pp / +36.3pp
- Dijkstra 75.2% 接近论文 60-70% (差距从 13-23pp缩至 ~5pp)
- ILP 求解 0.34s (与论文 CPLEX 0.32s 持平)
- 报告 06

## [2026-05-23] 简化为单种子模式 + 项目全面修复
- 移除多种子实验计划 (99/200), 聚焦 seed42。保留 `--seed` 和 `--data-dir` 接口
- P0: Git仓库初始化, 编写 README.md, pyproject.toml 添加 pyscipopt
- P1: spec.md/plan.md/configs 过期引用修正, HiGHS→SCIP
- P2: meta.yaml 新增 travel_time_std_ratio, results/ 清理, 求解器异常处理, _get_solver 去重
- P3: small 数据集重新生成 (CV 0.19→0.68), 移除冗余 import
- 报告 05

## [2026-05-22] 种子42最终实验: 路径匹配准确率 + 分析报告
- **关键修复**: 准确率从概率匹配改为路径向量匹配 (`np.array_equal`)。概率匹配高估 ~17pp
- **首次方差增大**: generator.py 方差参数 0.1-0.4 → 0.3-0.8, CV中位数 0.25 → 0.54
- ILP 100%, Dijkstra 83.5%, MILP 73.8% (CV=0.54)
- 报告 04

## [2026-05-21] 项目审计: 发现数据方差过低
- 根因: 行程时间 CV 中位数 0.25, 导致均值最短路径几乎总是最优
- 准确率偏离论文 18-37pp (MILP 97.8% vs 70-80%, Dijkstra 96.9% vs 60-70%)
- α 趋势颠倒: 论文 α↑→acc↑, 我们 α↑→acc↓
- 报告 03

## [2026-05-21] 求解器迁移: HiGHS → SCIP
- HiGHS 存在堆内存损坏bug (double free), 特定数据在单次求解内崩溃, 子进程隔离无效
- 迁移到 SCIP (pyscipopt 6.2.1 + PuLP SCIP_PY)。SCIP avg 0.77s (比CBC快2.7倍, 比HiGHS慢1.8倍但稳定)

## [2026-05-21] 重构: 数据生成与求解分离
- 新增 `data/generate.py` (--preset small/full), data目录按 small / full/seed* 组织
- RoadNetwork.save/load 序列化, run.py 新增 --data-dir, 删除临时脚本和多余配置

## [2026-05-21] Phase 3-4: 首次实验 + HiGHS求解器
- 65节点N=100实验: ILP 100%, MILP 97.3%, Dijkstra 96.5% (报告 01)
- HiGHS 比 CBC 快 4.8倍, N=500 实验: ILP 100%, MILP 98.0%, Dijkstra 97.1% (报告 02)

## [2026-05-21] Phase 1-2: 项目初始化 + 核心实现
- 项目结构, RSP级别共享venv (uv + Python 3.12)
- 核心算法: ILP精确解, MILP ℓ₁松弛, Dijkstra均值最短路
- 10/10单元测试通过, run.py一键入口 + YAML配置系统, 论文精读
