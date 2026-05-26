# TODO — 当前待办

## 当前阶段: Beijing Conflict 300-job 审计收口

Phase 1-9 全部完成。北京多级冲突方差 300-job 扩展实验完成（报告 21），当前重点是解释为什么 MILP 在北京冲突图上拉开优势，而不是继续加大规模。

## 重要文件路径

| 文件 | 说明 |
|------|------|
| `data/generate.py` | 数据生成脚本 (--preset small/full/beijing) |
| `data/full/seed42/` | 人工路网数据集 (65节点, CV=0.83) |
| `data/beijing/` | 北京路网数据集 (587节点, 1066边, CV=0.775, 高方差结果已完成) |
| `data/beijing_osm.graphml` | OSM路网拓扑 (预提取, GraphML格式) |
| `data/small/` | 小规模调试数据集 |
| `run.py` | CLI 实验入口 (--data-dir 切换数据) |
| `experiment.ipynb` | **优先运行入口**：调试 / 审计 / 交互式实验 |
| `configs/artificial_n500.yaml` | 人工路网实验配置 |
| `configs/beijing.yaml` | 北京路网实验配置 |
| `src/generator.py` | 数据生成逻辑 |
| `docs/change.md` | 变更日志 |
| `docs/report/index.html` | 报告索引页 |
| `docs/handover/004-delivery-handover.md` | **交付主文档**：接手顺序、关键文件、已知限制 |
| `docs/report/` | 历史报告 (01~21) |

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
- [x] 报告 17: 1000-job 大规模验证
- [x] 报告 18: metric policy rollout
- [x] 报告 19: conflict graph seed524
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
- [x] **主准确率切换** — summary / README / notebook / 图表 默认以 `tie_aware_accuracy` 作为主准确率展示
- [x] **路径匹配降级为辅助指标** — 保留 `path_match`，但移动到诊断区或次级表格
- [x] **gap 阈值策略定稿** — 默认固定 `|gap| ≤ 1/N`，不再继续复杂化
- [x] **清理 strict 相关代码与产物** — 清理 `tie_aware_accuracy_strict`、strict 图表、strict 汇总列
- [x] **新人工图 seed 524 方案** — 引入新的冲突型人工图实验族，不替代 `seed42`
- [x] **双峰边类型参数** —  
  `fast_risky`: `mean ~ U(10, 50)`, `cv ~ U(0.8, 1.4)`  
  `slow_stable`: `mean ~ U(40, 90)`, `cv ~ U(0.2, 0.6)`
- [x] **冲突结构检查** — 审计新图是否真的形成”快但险 vs 慢但稳”的可替代路径
- [x] **新人工图实验报告** — 跑 `seed524` 单组实验，比较 ILP / MILP / Dijkstra 的分离度与 gap 结构
- [ ] **冲突图机制证据补强** — 统计冲突 OD / 非冲突 OD、边类型占比、MILP 提升来源
- [x] **冲突图报告措辞收口** — 已修正报告 19 中 3 处过度声明
- [x] **北京冲突化方差方案** — 在北京真实拓扑上设计类似 `fast_risky / slow_stable` 的属性分层
- [x] **北京冲突化审计标准** — 先定义”什么叫真的制造了路径级冲突”，再安排跑实验
- [x] **北京多级冲突方差数据生成** — `--preset beijing-conflict` 落地, 预实验审计通过 (CV 分离干净, 4/10 OD 冲突)
- [x] **北京冲突化实验** — 跑 `beijing_conflict` 数据集, 比较 ILP / MILP / Dijkstra
- [x] **北京冲突化实验报告** — 分析北京多级方差下的求解器行为 (报告 20)
- [x] **北京冲突扩展实验（上限 300 jobs）** — 3 repeats × 20 OD × 5 α, 报告 21
- [ ] **北京基线对照表** — 用原始北京高方差基线（报告 10/12 口径）对照北京冲突结果，说明是“相对重排”还是“共同退化”
- [ ] **北京冲突机制证据补强** — conflict OD / non-conflict OD、边类型占比、MILP 增益来源
- [ ] **北京冲突报告措辞收口** — 把“历史最大”“设计验证成功”等强表述改成“初步/扩展结果支持”
- [ ] **北京结果解释补强后再刷新 notebook 输出** — `experiment.ipynb` 现已清空保存输出；若后续切回作为结果证据，必须用当前配置完整重跑
- [ ] **北京冲突低 α 行为** — 探索 α=0.3, 0.4 下 ℓ₁ 松弛的表现 (当前 α=0.5 时 MILP ≈ Dijkstra)
- [ ] **北京冲突解释收口后再扩展** — 在上面 5 项完成前，不继续扩大北京实验规模或增加更多方差层级

### 中优先级

- [x] **Candidate path / deadline 单元测试**: 已为 `generate_candidate_paths()` 和 `compute_deadline()` 增加回归测试

- [x] **PuLP 4.0 warning workaround**: 已切到本地兼容 helper，消除 `LpVariable(...)` deprecation warning

### 低优先级

- [ ] T-Drive 真实轨迹数据集成 (可选, 需获取数据)

## 快速命令

```bash
cd /home/kkk/projects/RSP

# 生成数据
uv run python Cao_SOTA_MP/data/generate.py --preset small
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42
uv run python Cao_SOTA_MP/data/generate.py --preset beijing
uv run python Cao_SOTA_MP/data/generate.py --preset beijing-conflict

# 跑实验
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/beijing.yaml --data-dir Cao_SOTA_MP/data/beijing --plot
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/beijing.yaml --data-dir Cao_SOTA_MP/data/beijing_conflict --plot

# 测试
uv run pytest Cao_SOTA_MP/tests/ -v
```
