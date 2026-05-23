# TODO - 当前待办

## 当前阶段: Phase 4b (数据修复 + 多种子对比实验)

## 重要文件路径

| 文件 | 说明 |
|------|------|
| `data/generate.py` | 数据生成脚本 |
| `data/full/seed*/` | 3个full数据集 (42, 99, 200) |
| `run.py` | 唯一实验入口(--data-dir切换seed) |
| `configs/artificial_n500.yaml` | 实验配置 (SCIP求解器) |
| `src/generator.py` | 数据生成逻辑 (已修复方差参数) |
| `docs/change.md` | 变更日志 |
| `docs/result/` | 历史报告 |

## 已完成
- [x] Phase 1-2: 环境 + 核心算法 + 测试(10/10)
- [x] Phase 3: 65节点N=100实验 (CBC, ILP 100%)
- [x] Phase 4: HiGHS + N=500实验(seed=42) → SCIP迁移
- [x] Phase 4b重构: 数据生成分离, 3个数据集(42/99/200)
- [x] 求解器迁移: HiGHS → SCIP (HiGHS内存崩溃)
- [x] 种子42 SCIP实验: ILP 100%, MILP 97.8%, Dijkstra 96.9%
- [x] 全面审计: 算法实现正确，根因是数据方差过低(CV 0.25)
- [x] 审计报告: docs/result/03_audit_seed42.html
- [x] 修复: generator.py 方差参数 0.1-0.4 → 0.3-0.8

- [x] 重新生成3个数据集 (seed=42/99/200) — 2026-05-22 20:32 (旧CV)
- [x] 种子42实验 → ILP 100%, Dijkstra 83.5%, MILP 73.8%
- [x] 种子42分析报告 → docs/result/04_seed42_final.html
- [x] 准确率指标修复: 概率匹配 → 路径向量匹配 (_path_match)
- [x] 二次增大方差: Uniform(0.3, 0.8) → Uniform(0.5, 1.2), CV中位数 0.54 → 0.83
- [x] 重新生成3个数据集 (新CV) — 2026-05-22
- [x] 项目状态评估报告 → docs/result/05_project_status.html
- [x] 修复P0问题: Git初始化 + README.md编写
- [x] 修复P1问题: spec.md/plan.md过期引用 + config注释
- [x] 修复P2问题: meta.yaml加方差记录, results清理, solve()异常处理, _get_solver去重
- [x] 修复P3问题: small数据集重新生成(CV=0.68), 冗余import移除
- [x] pyproject.toml: 添加pyscipopt依赖
- [ ] 种子42实验 (新高方差数据, CV=0.83)
- [ ] 种子99实验
- [ ] 种子200实验
- [ ] 3种子对比分析 + 总体报告

## 后续
- [ ] Phase 5: 可视化优化(论文Fig.2风格)
- [ ] Phase 6: 北京路网

## 快速命令

```bash
cd /home/kkk/projects/RSP

# 重新生成数据 (修复后方差)
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 99
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 200

# 跑实验
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed99 --plot
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed200 --plot

# 测试
uv run pytest Cao_SOTA_MP/tests/ -v
```
