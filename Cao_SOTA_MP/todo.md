# TODO - 当前待办

## 当前阶段: Phase 4b (数据修复 + 单种子实验)

## 重要文件路径

| 文件 | 说明 |
|------|------|
| `data/generate.py` | 数据生成脚本 (支持 --preset, --seed) |
| `data/full/seed42/` | 当前实验数据集 |
| `data/small/` | 小规模调试数据集 |
| `run.py` | 唯一实验入口 (--data-dir 切换数据) |
| `configs/artificial_n500.yaml` | 实验配置 (SCIP求解器) |
| `src/generator.py` | 数据生成逻辑 (CV: Uniform(0.5, 1.2)) |
| `docs/change.md` | 变更日志 |
| `docs/report/` | 历史报告 |

## 已完成
- [x] Phase 1-2: 环境 + 核心算法 + 测试(10/10)
- [x] Phase 3: 65节点N=100实验 (CBC, ILP 100%)
- [x] Phase 4: HiGHS + N=500实验 → SCIP迁移
- [x] Phase 4b重构: 数据生成分离, data按 small / full/seed* 组织
- [x] 求解器迁移: HiGHS → SCIP (HiGHS内存崩溃)
- [x] 全面审计: 算法实现正确，根因是数据方差过低(CV 0.25)
- [x] 审计报告: docs/report/03_audit_seed42.html
- [x] 修复: generator.py 方差参数 0.1-0.4 → 0.3-0.8 → 0.5-1.2
- [x] CV中位数: 0.25 → 0.54 → 0.83
- [x] 种子42实验 (CV=0.54) → ILP 100%, Dijkstra 83.5%, MILP 73.8%
- [x] 种子42分析报告 → docs/report/04_seed42_final.html
- [x] 准确率指标修复: 概率匹配 → 路径向量匹配 (_path_match)
- [x] 项目状态评估报告 → docs/report/05_project_status.html
- [x] P0-P3全面修复: Git提交, README, 文档对齐, 方差记录, 代码清理
- [x] 简化为单种子模式: 保留 --seed 接口, 清理多seed计划
- [x] 种子42高方差实验 (CV=0.83) → ILP 100%, Dijkstra 75.2%, MILP 63.7%
- [x] 结果报告 → docs/report/06_seed42_highvar.html

## 后续
- [ ] Phase 5: 可视化优化(论文Fig.2风格)
- [ ] Phase 6: 北京路网

## 快速命令

```bash
cd /home/kkk/projects/RSP

# 生成数据
uv run python Cao_SOTA_MP/data/generate.py --preset small
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42

# 跑实验
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot

# 测试
uv run pytest Cao_SOTA_MP/tests/ -v
```
