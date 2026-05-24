# TODO — 当前待办

## 当前阶段: Metric Policy + Expansion

Phase 1-9 全部完成。论文协议对齐和 notebook-first 入口已完成，当前先切换主评估口径，再做扩展型实验。

## 重要文件路径

| 文件 | 说明 |
|------|------|
| `data/generate.py` | 数据生成脚本 (--preset small/full/beijing) |
| `data/full/seed42/` | 人工路网数据集 (65节点, CV=0.83) |
| `data/beijing/` | 北京路网数据集 (587节点, 1066边, CV=0.775, 高方差结果已完成) |
| `data/beijing_osm.graphml` | OSM路网拓扑 (预提取, GraphML格式) |
| `data/small/` | 小规模调试数据集 |
| `run.py` | 唯一实验入口 (--data-dir 切换数据) |
| `experiment.ipynb` | **优先运行入口**：调试 / 审计 / 交互式实验 |
| `configs/artificial_n500.yaml` | 人工路网实验配置 |
| `configs/beijing.yaml` | 北京路网实验配置 |
| `src/generator.py` | 数据生成逻辑 |
| `docs/change.md` | 变更日志 |
| `docs/report/index.html` | 报告索引页 |
| `docs/report/` | 历史报告 (01~16) |

## 已完成

- [x] Phase 1-2: 环境 + 核心算法 + 测试(10/10)
- [x] Phase 3: 65节点N=100实验
- [x] Phase 4: N=500实验 (SCIP, ILP 100%)
- [x] Phase 4b: 审计 + 方差修复 (CV 0.83)
- [x] Phase 4b: 种子42最终实验 → ILP 100%, Dijkstra 75.2%, MILP 63.7%
- [x] Phase 7: 求解器优化 (tight big-M, 进度条, MILP诊断)
- [x] Phase 6: 北京路网实验 (OSM 587节点)
- [x] Phase 8: 审计修复全部完成 (求解器返回标准化, 候选路径池扩展, 新指标系统, worst_cases.csv)
- [x] 人工路网重跑验证 (seed42, 1000 jobs, 16.4min) → 报告 09
- [x] 北京路网重跑验证 (90 jobs, 142.7min) → 报告 10
- [x] 北京路网 CV 增大 (osm_network.py: CV范围上移 ~0.2)
- [x] 北京路网高方差数据重新生成 (CV median 0.54→0.775)
- [x] 项目全面审计 + 状态报告 → 报告 11
- [x] 文档规范化: 明确各文档职责, todo.md 移入 docs/
- [x] Jupyter Notebook 创建: experiment.ipynb 复现 run.py 工作流, 32 个 cell 逐节可执行
- [x] 报告 12: 北京路网高方差实验结果分析
- [x] 报告 14: small 数据集 deadline 协议审计（heuristic vs exact）
- [x] 报告 15: full/seed42 notebook rerun 正式结果
- [x] 报告 16: full/seed42 详细复盘与状态审计
- [x] 维护对齐: README / plan / todo / spec / handover 与 report 12 状态同步
- [x] Beijing meta.yaml 补充 highway_cv_range
- [x] 报告 13: 维护/审计跟进与任务排程
- [x] 论文协议对齐：`deadline.mode = heuristic / exact`
- [x] ILP 非最优样本完整记账：结果表保留 `status` / `reference_available`
- [x] Notebook-first 入口对齐：`experiment.ipynb` 暴露协议开关并复用 `run_experiment()`

## 待做

### 高优先级

- [x] **Phase 5: 可视化优化** — 已输出升级版 Fig.2 风格图和 `compute_time_summary.csv`
- [x] **论文协议对齐：deadline 严格模式** — 小图/审计模式下支持枚举所有路径计算 `τ`
- [x] **论文协议对齐：ILP 非最优样本完整记账** — 不再跳过 `status != Optimal` 的 job
- [x] **Notebook-first 入口对齐** — `experiment.ipynb` 配置区暴露 `deadline.mode` 与审计开关
- [ ] **主准确率切换** — summary / README / notebook / 图表 默认以 `tie_aware_accuracy` 作为主准确率展示
- [ ] **路径匹配降级为辅助指标** — 保留 `path_match`，但移动到诊断区或次级表格
- [ ] **阈值敏感性实验** — 比较 `|gap| ≤ 1/N` 与一个统一更严格阈值（如 `0.5/N`）对排名和结论的影响

### 中优先级

- [x] **Candidate path / deadline 单元测试**: 已为 `generate_candidate_paths()` 和 `compute_deadline()` 增加回归测试

- [x] **PuLP 4.0 warning workaround**: 已切到本地兼容 helper，消除 `LpVariable(...)` deprecation warning

- [ ] **多 seed 统计显著性实验**：在协议对齐后重跑人工路网，输出均值/方差

### 低优先级

- [ ] T-Drive 真实轨迹数据集成 (可选, 需获取数据)

## 快速命令

```bash
cd /home/kkk/projects/RSP

# 生成数据
uv run python Cao_SOTA_MP/data/generate.py --preset small
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42
uv run python Cao_SOTA_MP/data/generate.py --preset beijing

# 跑实验
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/beijing.yaml --data-dir Cao_SOTA_MP/data/beijing --plot

# 测试
uv run pytest Cao_SOTA_MP/tests/ -v
```
