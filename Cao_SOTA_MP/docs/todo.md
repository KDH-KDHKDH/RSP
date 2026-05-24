# TODO — 当前待办

## 当前阶段: Post-Phase 9 Maintenance

Phase 1-9 全部完成。ILP=100% 精确解已复现。本轮维护和可视化补强已完成，当前仅保留扩展型任务。

## 重要文件路径

| 文件 | 说明 |
|------|------|
| `data/generate.py` | 数据生成脚本 (--preset small/full/beijing) |
| `data/full/seed42/` | 人工路网数据集 (65节点, CV=0.83) |
| `data/beijing/` | 北京路网数据集 (587节点, 1066边, CV=0.775, 高方差结果已完成) |
| `data/beijing_osm.graphml` | OSM路网拓扑 (预提取, GraphML格式) |
| `data/small/` | 小规模调试数据集 |
| `run.py` | 唯一实验入口 (--data-dir 切换数据) |
| `configs/artificial_n500.yaml` | 人工路网实验配置 |
| `configs/beijing.yaml` | 北京路网实验配置 |
| `src/generator.py` | 数据生成逻辑 |
| `docs/change.md` | 变更日志 |
| `docs/report/index.html` | 报告索引页 |
| `docs/report/` | 历史报告 (01~13) |

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
- [x] 维护对齐: README / plan / todo / spec / handover 与 report 12 状态同步
- [x] Beijing meta.yaml 补充 highway_cv_range
- [x] 报告 13: 维护/审计跟进与任务排程

## 待做

### 高优先级

- [x] **Phase 5: 可视化优化** — 已输出升级版 Fig.2 风格图和 `compute_time_summary.csv`

### 中优先级

- [x] **Candidate path / deadline 单元测试**: 已为 `generate_candidate_paths()` 和 `compute_deadline()` 增加回归测试

- [x] **PuLP 4.0 warning workaround**: 已切到本地兼容 helper，消除 `LpVariable(...)` deprecation warning

### 低优先级

- [ ] T-Drive 真实轨迹数据集成 (可选, 需获取数据)
- [ ] 多 seed 统计显著性实验（在需要论文级统计结论时再做）

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
