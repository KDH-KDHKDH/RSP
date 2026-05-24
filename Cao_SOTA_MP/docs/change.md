# 变更日志 (Changelog)

## [2026-05-24] 维护对齐 + 元数据追溯修复
- README / plan / todo / spec 对齐到 report 12 之后的真实状态，移除“北京高方差待跑”的过时表述
- Beijing 数据生成元数据补全：`data/generate.py` 现在写入 `highway_cv_range`，`data/beijing/meta.yaml` 已同步补齐
- `network_source` 统一为离线 GraphML/PBF 提取表述，避免与文档中的 `osmium` 离线流程冲突
- 新增报告 13: `docs/report/13_maintenance_followup.html`，用于承接 report 11 中已被后续结果更新的维护/审计结论
- 报告索引与 handover 更新，明确 report 09 / 12 为当前结果；report 07 的 MILP 抽样偏差改由后续维护报告说明，不覆写历史编号报告

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
