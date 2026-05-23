# 变更日志 (Changelog)

## [2026-05-23] 简化为单种子模式
- 移除多种子实验计划 (99/200)，聚焦单种子 (seed42)
- 保留 `--seed` 和 `--data-dir` 接口 (可随时切换种子)
- 清理 data/full/seed99, data/full/seed200 数据目录
- 更新所有文档: todo, plan, spec, README, config 注释

## [2026-05-23] 项目全面修复 (P0-P3)
- **P0**: Git仓库初始化 (移除嵌套.git), 编写 README.md (项目描述、快速开始、架构)
- **P0**: pyproject.toml 添加 pyscipopt 依赖
- **P1**: spec.md 过期引用修复 (种子名 123/456→99/200, HiGHS→SCIP, 移除不存在的文件)
- **P1**: plan.md 报告引用修正 (03_scip→03_audit, 编号04/05/06对齐)
- **P1**: configs/artificial_n500.yaml 过期注释修复
- **P2**: data/generate.py meta.yaml 新增 travel_time_std_ratio 字段
- **P2**: results/ 目录清理 (删除7个中间/过时实验目录)
- **P2**: ilp_solver + milp_solver 添加 solve() 异常处理
- **P2**: _get_solver() 去重 (milp_solver 改为从 ilp_solver 导入)
- **P3**: small 数据集重新生成 (CV 0.19→0.68)
- **P3**: generator.py 移除冗余 import networkx as nx
- 所有4个数据集已用最新参数重新生成 (travel_time_std_ratio 已记录)

## [2026-05-23] 项目状态评估报告
- 全面审计: 代码 (1013行) · 数据 (4个数据集) · 结果 (1个完成实验) · 文档 (7个文件) · 测试 (10/10)
- 核心算法正确，ILP 100%精确解已复现
- 发现 12 个问题 (P0: 2, P1: 3, P2: 4, P3: 3)
- 最严重: Git零提交、README为空、spec.md过期引用、meta.yaml不记录方差
- 报告: docs/report/05_project_status.html

## [2026-05-22] 二次增大行程时间方差
- **修复**: `generator.py` 方差参数从 `Uniform(0.3, 0.8)` 改为 `Uniform(0.5, 1.2)`
- CV 中位数从 0.54 提升到 0.83 (范围 0.48~1.51)
- 目的: 制造更多"均值最优 ≠ 准时最优"场景，提升问题难度
- 3个数据集已重新生成 (seed42/99/200)
- 旧报告 (04_seed42_final.html) 基于 CV=0.54 数据，将被新高方差结果取代

## [2026-05-22] 种子42最终实验: 路径匹配准确率 + 分析报告
- **关键修复**: 准确率指标从概率匹配改为路径向量匹配 (`_path_match` with `np.array_equal`)
- 概率匹配会高估准确率 ~17pp（不同路径可能有相同准时概率）
- ILP 100%, Dijkstra 83.5%, MILP 73.8% — ILP 显著优于 baselines
- ILP vs Dijkstra +16.5pp, ILP vs MILP +26.2pp
- 准时概率差距 < 0.001（问题难度仍偏低但核心结论成立）
- α 趋势与论文仍有差异（可能因论文 deadline 参数未公开）
- 报告: docs/report/04_seed42_final.html

## [2026-05-22] 数据生成修复: 增大行程时间方差
- **修复**: `generator.py` 方差参数从 `Uniform(0.1, 0.4)` 改为 `Uniform(0.3, 0.8)`
- CV 中位数预计从 0.25 提升到 ~0.55，使问题实例难度与论文可比
- 预期效果: Dijkstra 准确率降至 60-70%, MILP 降至 70-80%, α 趋势恢复递增
- 需要重新生成 3 个种子数据集并重跑实验验证
- 更新 docs/plan.md, docs/todo.md 反映审计发现和修复

## [2026-05-21] 项目审计：发现数据生成问题（当前阻塞）
- 全面审计 ILP/MILP/Dijkstra 算法实现：✓ 三个求解器与论文一致
- 发现准确率与论文存在 18-37pp 偏差：MILP 97.8% vs 论文 70-80%, Dijkstra 96.9% vs 论文 60-70%
- **根因**: 行程时间 CV 过低 (中位数 0.25)，导致均值最短路径几乎总是最优
- 准确率 vs α 趋势颠倒：论文 α↑→acc↑, 我们 α↑→acc↓
- 修复方案：扩大 generator.py 方差参数 (std/mean 从 0.1-0.4 改为 0.3-0.8)
- 报告: docs/report/03_audit_seed42.html

## [2026-05-21] 求解器迁移: HiGHS → SCIP + 种子42实验完成
- HiGHS 存在堆内存损坏 bug (<code>double free</code>)，特定数据（种子99）在单次求解内崩溃，子进程隔离无效
- 迁移到 SCIP 求解器 (pyscipopt 6.2.1 + PuLP SCIP_PY 接口)
- `_get_solver()` 新增 SCIP 选项: `pulp.SCIP_PY(msg=0, timeLimit=time_limit)`
- SCIP 性能: ILP avg 0.77s (比 CBC 快 2.7 倍，比 HiGHS 慢 1.8 倍但稳定)
- 种子42 N=500实验完成: ILP 100%, MILP 97.8%, Dijkstra 96.9%
- 发现: α 对方法优劣影响显著，低 α 时 Dijkstra 反超 MILP
- `run.py` 新增 `sys.stdout.reconfigure(line_buffering=True)` 修复管道缓冲问题
- 报告: docs/report/03_scip_seed42.html (已被审计报告取代)

## [2026-05-21] 重构: 数据生成与算法主流程分离
- 新增 `data/generate.py` 数据生成脚本(支持 --preset small/full, --seed)
- data目录按 small / full/seed* / beijing 组织
- `src/graph.py` 添加 RoadNetwork.save() / RoadNetwork.load() 序列化方法
- `src/experiment.py` 新增 load_experiment_data()，支持从文件加载数据
- `run.py` 简化为唯一入口，新增 `--data-dir` 参数覆盖数据路径
- 配置文件简化: 去掉 network 段，新增 data.dir 字段
- 删除临时脚本: run_single_repeat.py, run_multi_seed.py
- 删除多余配置: artificial_full.yaml, artificial_small.yaml, seed123/456 yaml
- 生成3个full数据集: seed42, seed99, seed200 (替换原 seed123/456)

## [2026-05-21] Phase 4: HiGHS求解器 + N=500实验
- 安装HiGHS求解器(highspy v1.14.0)，比CBC快4.8倍
- `_get_solver()` 改用 `pulp.HiGHS` Python API(避免需要外部二进制)
- N=500实验完成(seed=42): ILP 100%, MILP 98.0%, Dijkstra 97.1%
- 求解器对比: CBC avg 2.06s vs HiGHS avg 0.42s (ILP)
- 报告: docs/report/02_n500_solver_compare.html

## [2026-05-21] Phase 3: 65节点实验
- 65节点N=100实验完成: ILP 100%, MILP 97.3%, Dijkstra 96.5%
- 枚举优化: 用ILP作为ground-truth(论文已证明精确)
- 报告: docs/report/01_initial_65node.html

## [2026-05-21] Phase 1-2: 项目初始化 + 核心实现
- 项目结构搭建，RSP级别共享venv(uv + Python 3.12)
- 核心算法: ILP精确解、MILP ℓ₁松弛、Dijkstra均值最短路
- 10/10单元测试通过
- run.py一键入口 + YAML配置系统
- 论文精读(docs/paper.html)、规格文档(docs/spec.md)
