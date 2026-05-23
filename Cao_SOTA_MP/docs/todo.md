# TODO — 当前待办

## 当前阶段: Phase 5 + Phase 9

Phase 1-8 全部完成。ILP=100% 精确解已复现。待推进可视化优化和北京高方差实验。

## 重要文件路径

| 文件 | 说明 |
|------|------|
| `data/generate.py` | 数据生成脚本 (--preset small/full/beijing) |
| `data/full/seed42/` | 人工路网数据集 (65节点, CV=0.83) |
| `data/beijing/` | 北京路网数据集 (587节点, 1066边, CV=0.775, 高方差数据已生成) |
| `data/beijing_osm.graphml` | OSM路网拓扑 (预提取, GraphML格式) |
| `data/small/` | 小规模调试数据集 |
| `run.py` | 唯一实验入口 (--data-dir 切换数据) |
| `configs/artificial_n500.yaml` | 人工路网实验配置 |
| `configs/beijing.yaml` | 北京路网实验配置 |
| `src/generator.py` | 数据生成逻辑 |
| `docs/change.md` | 变更日志 |
| `docs/report/index.html` | 报告索引页 |
| `docs/report/` | 历史报告 (01~11) |

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

## 待做

### 高优先级

- [ ] **北京路网高方差实验重跑**: 数据已生成 (CV=0.775)，需验证新CV下基线方法表现
  ```bash
  uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/beijing.yaml --data-dir Cao_SOTA_MP/data/beijing --plot
  ```
  预计耗时: ~140 min (候选路径池 1000)

### 中优先级

- [ ] **Phase 5: 可视化优化** — 论文 Fig.2 风格
  - [ ] 准确率 vs α 折线图 (已有基础版)
  - [ ] ILP vs 其他方法准时概率散点图 (已有基础版)
  - [ ] Table I: 计算时间对比表

- [ ] **Report 07 MILP 数据加注**: MILP=78.3% 仅基于 2 repeats，与权威报告 09 的 63.7% 不一致。在报告 07 中加注说明抽样限制

- [ ] **Beijing meta.yaml 补充 CV 范围**: 在 `data/generate.py` 中为 beijing preset 写入 `highway_cv_range` 字段

### 低优先级

- [ ] spec.md 验收标准北京路网部分待高方差实验后填写实际数据
- [ ] T-Drive 真实轨迹数据集成 (可选, 需获取数据)
- [ ] PuLP 4.0 API 迁移 (LpVariable → add_variable, 消除 100 个 deprecation warning)

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
