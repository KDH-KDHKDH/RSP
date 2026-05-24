# 001 Project Handover — Cao SOTA MP

**Date:** 2026-05-23
**Status:** Core implementation complete. Beijing high-CV experiment pending re-run.
**Tests:** 10/10 passing.

---

## 1. What This Project Is

Reproduction of **Cao et al. (2020)** — "Finding the Shortest Path with Maximum Punctuality Probability under Stochastic Travel Times." An ILP-based exact solver that finds the path maximizing the probability of arriving on-time, given lognormal stochastic edge travel times and a user-specified deadline τ.

**Key insight:** The paper proves ILP = exact solution, so no path enumeration is needed for ground-truth evaluation on large graphs.

## 2. Current Progress

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1–2: Core implementation | Done | ILP, MILP, Dijkstra solvers; 10/10 tests |
| Phase 3: 65-node N=100 | Done | Initial verification |
| Phase 4: N=500 + SCIP | Done | HiGHS abandoned (memory bug), migrated to SCIP |
| Phase 4b: Variance audit + fix | Done | CV increased 0.25 → 0.83 (2 rounds of fixes) |
| Phase 5: Paper-quality viz | **Pending** | Basic plots exist, not paper-grade |
| Phase 6: Beijing OSM network | Done | 587 nodes, 1066 edges, OSM topology |
| Phase 7: Solver optimization | Done | Tight big-M, progress bar, MILP diagnosis |
| Phase 8: Audit fix | Done | Standardized returns, expanded candidate paths, new metrics |

### What Works
- ILP finds the optimal path (verified against enumeration on small graphs)
- MILP ℓ₁ relaxation and Dijkstra mean-SP baselines
- Both artificial (65-node) and Beijing OSM (587-node) networks
- Two accuracy metrics: strict path-match + tie-aware (|gap| ≤ 1/N)
- Tight per-sample big-M: ILP solve time matches paper's CPLEX (0.33s)
- 11 experiment reports in `docs/report/`

### What's Blocked / Pending
- **Beijing high-CV re-run** (data ready, ~140 min, stopped by user request)
- Phase 5 paper-quality visualization
- T-Drive real trajectory data integration (optional)

## 3. Quick Start Commands

```bash
cd /home/kkk/projects/RSP

# Generate data
uv run python Cao_SOTA_MP/data/generate.py --preset small          # 10-node debug
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42 # 65-node artificial
uv run python Cao_SOTA_MP/data/generate.py --preset beijing        # Beijing OSM

# Run experiments
uv run python Cao_SOTA_MP/run.py                                                        # default (data/small)
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot         # artificial
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/beijing.yaml \
    --data-dir Cao_SOTA_MP/data/beijing --plot                                           # Beijing

# Run tests (always do this first)
uv run pytest Cao_SOTA_MP/tests/ -v
```

## 4. Architecture (Key Files)

```
Cao_SOTA_MP/
├── src/
│   ├── graph.py              # RoadNetwork dataclass + incidence matrix Mx = b
│   ├── generator.py          # Graph generation + deadline computation
│   │                         #   deadline: τ = T_min + α·(T_max - T_min)
│   │                         #   T_max = minimax path time (min over paths of max sample time)
│   │                         #   Candidate paths: 4 sources, max 1000, deduplicated
│   ├── osm_network.py        # Beijing OSM loading (GraphML) + CV/speed mappings
│   ├── ilp_solver.py         # ILP exact solver (min Σιᵢ, tight big-M)
│   ├── milp_solver.py        # MILP ℓ₁ relaxation (min Σpᵢ, p continuous)
│   ├── dijkstra_solver.py    # Mean-weight shortest path baseline
│   ├── experiment.py         # Orchestration: load data, run all solvers, collect metrics
│   └── visualize.py          # Plots + print_summary
├── data/
│   ├── generate.py           # Standalone data generation (--preset small/full/beijing)
│   ├── small/                # 10-node debug dataset
│   ├── full/seed42/          # 65-node artificial (CV=0.83)
│   ├── beijing/              # 587-node Beijing OSM (CV=0.775, experiment NOT run yet)
│   └── beijing_osm.graphml   # Pre-extracted OSM topology
├── configs/
│   ├── default.yaml          # Points to data/small
│   ├── artificial_n500.yaml  # 65-node experiment config
│   └── beijing.yaml          # Beijing experiment config
├── run.py                    # Single entry point (--data-dir, --config, --plot)
├── tests/test_solvers.py     # 10 tests (graph ops + solver correctness)
└── docs/
    ├── paper.html            # Paper reading notes (Chinese)
    ├── spec.md               # Specification (algorithms, interfaces, formats)
    ├── plan.md               # Phased implementation plan + key decisions
    ├── change.md             # Changelog (detailed, chronological)
    ├── todo.md               # Current TODO list
    └── report/               # 11 experiment reports + index.html
```

## 5. Solver Interface (All 3 Solvers Share This)

```python
def solve_xxx(network: RoadNetwork, W: np.ndarray,      # W: N × |L| travel time samples
              origin: int, destination: int, tau: float, # tau: deadline
              ...) -> dict:
    return {
        "path_x": np.ndarray,        # binary edge selection vector (|L|,)
        "lateness_count": int,       # number of late samples
        "punctuality_prob": float,   # 1 - lateness_count/N
        "status": str,               # "Optimal" / "NoPath" / "SolverError: ..."
        "solve_time": float,         # seconds
    }
```

## 6. Data Flow

```
data/generate.py  →  data/{preset}/  (network.npz, travel_times.npz, od_pairs.npy, meta.yaml)
                                         ↓
run.py  →  experiment.run_experiment()  →  for each (repeat, OD pair, alpha):
                                              1. compute_deadline(τ) via candidate paths
                                              2. solve_ilp()    → ground-truth
                                              3. solve_milp()   → ℓ₁ relaxation
                                              4. solve_dijkstra() → mean-SP baseline
                                         →  results.csv + figures + worst_cases.csv
```

## 7. Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Ground-truth | ILP itself | Paper proves ILP = exact solution |
| Solver | SCIP 6.2.1 (pyscipopt) | Stable open-source; HiGHS had memory corruption bug |
| big-M | Per-sample tight: Mᵢ = max(1, ΣⱼW[i,j]-τ) | 200–8000× tighter than fixed 1e6 |
| Candidate paths | 4 sources (mean SP, worst-case SP, per-sample SPs, K-shortest) | Max 1000, deduplicated, priority-ordered |
| Accuracy metrics | Path-match + tie-aware (\|gap\| ≤ 1/N) | Path-match can be misleading when punctuality differences < sampling error |
| Data/solve separation | `data/generate.py` produces dirs, `run.py` consumes them | Isolates topology issues from solver issues |
| Venv | Shared at RSP/ level (uv + pyproject.toml) | Single venv for all RSP subprojects |

## 8. Variance History (Critical for Result Interpretation)

The project went through 3 variance levels for the artificial network:

| Round | std/mean range | CV median | Dijkstra acc | MILP acc | When |
|-------|---------------|-----------|-------------|----------|------|
| 1 (too low) | Uniform(0.1, 0.4) | 0.25 | 96.9% | 97.8% | Initial |
| 2 (moderate) | Uniform(0.3, 0.8) | 0.54 | 83.5% | 73.8% | After 1st fix |
| 3 (current) | Uniform(0.5, 1.2) | 0.83 | 75.2% | 63.7% | After 2nd fix |

Beijing CV also increased: trunk/primary 0.3–0.5 → 0.5–0.8, secondary 0.5–0.8 → 0.7–1.1, residential 0.8–1.2 → 0.9–1.3. Median 0.54 → 0.775 (data regenerated, experiment pending).

## 9. How to Read the Reports

Open `docs/report/index.html` in a browser for a navigable index. Key reports:

| # | Report | What It Shows |
|---|--------|---------------|
| 03 | audit_seed42 | Discovered the low-variance root cause (CV=0.25 → inflated accuracy) |
| 06 | seed42_highvar | Final artificial network results (CV=0.83, path-match only) |
| 07 | seed42_tightM | Validated tight big-M optimization (ILP time -39%) |
| 09 | seed42_audit_fix | **Definitive artificial results** with full Phase 8 metrics |
| 10 | beijing_audit_fix | **Definitive Beijing results** (old CV, full Phase 8 metrics) |
| 11 | project_audit | Comprehensive project audit (code, data, results, docs) |
| 08 | beijing | Original Beijing experiment (before Phase 8 fixes) |

**When reading historical results, start from reports 09 and 10 because they were the latest results at that stage.** Report 07's MILP=78.3% is inflated (only 2 repeats vs 3 in report 09).

## 10. Known Issues (Non-Blocking)

1. **Beijing high-CV experiment not run** — data regenerated (CV=0.775) but experiment was stopped. Needs ~140 min.
2. **Beijing meta.yaml missing CV range** — unlike artificial network's `travel_time_std_ratio`, Beijing doesn't record which CV ranges were used.
3. **spec.md acceptance criteria stale** — references old CV=0.54 accuracy numbers (low priority).
4. **No candidate path generation tests** — logic is exercised through integration tests (experiment runs) but lacks dedicated unit tests.
5. **PuLP deprecation warning** — `LpVariable(name, ...)` deprecated in PuLP 4.0; should migrate to `prob.add_variable(...)`. Cosmetic, 100 warnings in test output.

## 11. Next Steps (Priority Order)

### Immediate (unblock the project)
```bash
# Re-run Beijing experiment with high-CV data (data already generated)
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/beijing.yaml \
    --data-dir Cao_SOTA_MP/data/beijing --plot
# Expected: ~140 min, will produce results/beijing/results.csv + figures
# Then update reports 08 and 10 with new data
```

### Short-term
- Phase 5: Paper-quality visualizations (Fig.2(a)(b)(c), Table I)
- Add `highway_cv_range` to Beijing meta.yaml in `data/generate.py`
- Fix report 07 MILP note about 2-repeat sampling variance

### Nice-to-have
- T-Drive GPS trajectory data integration for Beijing
- Multi-seed experiments for statistical significance
- PuLP 4.0 API migration (add_variable)

## 12. If Something Breaks

1. **Tests fail:** Run `uv run pytest Cao_SOTA_MP/tests/ -v`. The `test_ilp_returns_optimal` test verifies ILP against full enumeration — if this fails, the solver logic is wrong.
2. **SCIP not found:** Check `uv sync` completed. pyscipopt requires SCIP libraries.
3. **Beijing experiment hangs:** ILP can hit the 120s time limit on hard instances (α=0.5). This is expected — the solver returns the best feasible solution found.
4. **Memory issues:** Large candidate path pools (1000 paths × 500 samples) use significant RAM. Can reduce `max_paths` in config.
5. **Data regeneration:** Always safe to re-run `data/generate.py` — it overwrites cleanly. Network topology is deterministic for the same seed.

## 13. Key Concepts Glossary

| Term | Meaning |
|------|---------|
| **W** | N × \|L\| matrix of travel time samples (N scenarios, \|L\| edges) |
| **τ (tau)** | Deadline: τ = T_min + α·(T_max - T_min) |
| **T_max** | Minimax path time: min over paths of (max sample travel time on that path) |
| **T_min** | Min sample travel time on the minimax path |
| **α (alpha)** | Deadline tightness: 0.5 (tight) to 0.9 (loose) |
| **ιᵢ (iota)** | Binary indicator: 1 if path exceeds τ in sample i, else 0 |
| **M (big-M)** | Constraint coefficient: Wᵢ'x - M·ιᵢ ≤ τ. Tight per-sample: Mᵢ = max(1, ΣⱼW[i,j]-τ) |
| **Mx = b** | Flow conservation: incidence matrix × edge selection = OD vector |
| **objective_gap** | p_ILP - p_method (punctuality probability difference) |
| **tie_aware_correct** | True when \|gap\| ≤ 1/N (within sampling error) |
| **ℓ₁ relaxation** | MILP minimizes Σpᵢ (total delay) instead of Σιᵢ (late count) |
| **CV** | Coefficient of variation = std/mean per edge |

## 14. Reference Documents

| Document | Path | Purpose |
|----------|------|---------|
| Paper | `docs/2020-Cao-SOTA-MP.pdf` | Original paper |
| Paper notes | `docs/paper.html` | Detailed paper reading notes (Chinese) |
| Spec | `docs/spec.md` | Algorithm specs, interface contracts, acceptance criteria |
| Plan | `docs/plan.md` | Phased plan, key decisions, report inventory |
| Changelog | `docs/change.md` | Chronological log of all changes |
| TODO | `docs/todo.md` | Current task list |
| Report index | `docs/report/index.html` | Navigable index of all 11 reports |
| CLAUDE.md | `../CLAUDE.md` | AI assistant instructions (at RSP level) |
