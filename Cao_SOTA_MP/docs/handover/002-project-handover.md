# 002 Project Handover — Cao SOTA MP

**Date:** 2026-05-24
**Status:** Phase 1-9 complete. ILP 100% exact solution reproduced on both networks. All pending experiments done.
**Tests:** 10/10 passing.
**Previous handover:** 001 (2026-05-23) — Beijing high-CV was pending then; now complete.

---

## 1. What This Project Is

Reproduction of **Cao et al. (2020)** — "Finding the Shortest Path with Maximum Punctuality Probability under Stochastic Travel Times." An ILP-based exact solver that finds the path maximizing the probability of arriving on-time given stochastic edge travel times and a user-specified deadline τ.

**Key insight:** The paper proves ILP = exact solution — no path enumeration needed for ground-truth evaluation.

## 2. Current Progress (All Phases)

| Phase | Status | Key Result |
|-------|--------|------------|
| Phase 1–2: Core implementation | Done | ILP, MILP, Dijkstra solvers; 10/10 tests |
| Phase 3: 65-node N=100 | Done | Initial verification |
| Phase 4: N=500 + SCIP | Done | HiGHS abandoned (memory bug), SCIP adopted |
| Phase 4b: Variance fix round 2 | Done | CV 0.25→0.54→0.83; fixed by adjusting std/mean ranges |
| Phase 6: Beijing OSM network | Done | 587 nodes, 1066 edges, OSM topology via osmium |
| Phase 7: Solver optimization | Done | Tight per-sample big-M; ILP -39% (0.54s→0.33s) |
| Phase 8: Audit + fixes | Done | Standardized solver returns, candidate path pool (4 sources, max 1000), tie-aware metrics, worst_cases.csv |
| Phase 9: Beijing high-CV | **Done** | CV 0.775; ILP 100%, Dijkstra 71.1%, MILP 68.9% |
| Phase 5: Paper-quality viz | Done | Fig.2-style plots upgraded; compute-time summary exported |

## 3. Definitive Results

### Artificial Network (65-node, CV=0.83, report 09)

| Method | Path-Match | Tie-Aware | Solve Time |
|--------|-----------|-----------|------------|
| ILP | 100% | 100% | 0.34s |
| Dijkstra | 75.2% | 88.3% | 0.0003s |
| MILP | 63.7% | 90.2% | 0.17s |

### Beijing OSM (587-node, CV=0.775, report 12) — Latest in this repo

| Method | Path-Match | Tie-Aware | Solve Time |
|--------|-----------|-----------|------------|
| ILP | 100% | 100% | 23.3s |
| Dijkstra | 71.1% | 90.0% | 0.004s |
| MILP | 68.9% | 88.9% | 7.7s |

**Key finding:** Higher CV widens ILP advantage in strict path-match terms. At the same time, Beijing's grid topology creates a flat punctuality surface, so tie-aware metrics (both ~90%) better reflect practical performance and are the planned primary comparison metric for later maintenance.

## 4. Quick Start

```bash
cd /home/kkk/projects/RSP

# Generate data
uv run python Cao_SOTA_MP/data/generate.py --preset small          # 10-node debug
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42 # 65-node (CV=0.83)
uv run python Cao_SOTA_MP/data/generate.py --preset beijing        # Beijing OSM (CV=0.775)

# Run experiments
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/beijing.yaml \
    --data-dir Cao_SOTA_MP/data/beijing --plot

# Interactive (Jupyter)
# Open Cao_SOTA_MP/experiment.ipynb in VS Code

# Tests
uv run pytest Cao_SOTA_MP/tests/ -v
```

## 5. Architecture

```
Cao_SOTA_MP/
├── src/
│   ├── graph.py              # RoadNetwork dataclass + incidence matrix Mx = b
│   ├── generator.py          # Graph generation + deadline (τ = T_min + α·(T_max - T_min))
│   ├── osm_network.py        # Beijing OSM loading (GraphML) with highway-attributed CV/speed
│   ├── ilp_solver.py         # ILP exact solver (min Σιᵢ, tight per-sample big-M)
│   ├── milp_solver.py        # MILP ℓ₁ relaxation (min Σpᵢ, continuous p)
│   ├── dijkstra_solver.py    # Mean-weight shortest path baseline
│   ├── experiment.py         # Orchestration: load → iterate → collect
│   └── visualize.py          # Plots + print_summary
├── data/
│   ├── generate.py           # --preset small / full / beijing
│   ├── small/                # 10-node debug
│   ├── full/seed42/          # 65-node (CV=0.83)
│   ├── beijing/              # 587-node generated dataset (CV=0.775, 10 repeats, 20 OD, N=500)
│   └── beijing_osm.graphml   # Pre-extracted OSM topology (osmium PBF → GraphML)
├── configs/                  # YAML: default / artificial_n500 / beijing
├── experiment.ipynb          # 32-cell Jupyter notebook replicating run.py
├── run.py                    # Single entry point
├── tests/test_solvers.py     # 10 tests (graph + solver correctness)
└── docs/
    ├── change.md             # Chronological changelog
    ├── plan.md               # Phases, decisions, report inventory
    ├── spec.md               # Primary spec (interfaces, acceptance criteria)
    ├── todo.md               # Granular actionable tasks + completed history
    ├── paper.html            # Paper reading notes (Chinese)
    ├── report/               # 17 numbered HTML reports + index.html
    └── handover/             # Handover documents (001, 002)
```

## 6. Data Flow

```
data/generate.py  →  data/{preset}/  (network.npz, travel_times.npz, od_pairs.npy, meta.yaml)
                                         ↓
run.py  →  for each (repeat, OD pair, alpha):
              1. compute_deadline(τ) — candidate paths (mean SP, worst SP, per-sample SP, K-shortest)
              2. solve_ilp()    → ground-truth
              3. solve_milp()   → ℓ₁ relaxation
              4. solve_dijkstra() → mean-SP baseline
         →  results.csv + figures + worst_cases.csv
```

## 7. Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Ground-truth | ILP itself | Paper proves ILP = exact solution |
| Solver | SCIP 6.2.1 (pyscipopt) | Stable open-source; HiGHS had memory corruption |
| big-M | Per-sample: Mᵢ = max(1, ΣⱼW[i,j]-τ) | 200–8000× tighter than fixed 1e6 |
| Candidate paths | 4 sources, max 1000, deduplicated | Wide coverage without explosion |
| Metrics | tie-aware as primary, path-match as secondary (\|gap\| ≤ 1/N) | Path-match alone misleading when punctuality differences < sampling error |
| Data/solve separation | `data/generate.py` → data dirs → `run.py` | Isolates topology from solver issues |
| Venv | Shared at RSP/ level (uv + pyproject.toml) | Single venv for all RSP subprojects |

## 8. Solver Interface (All 3 Share This)

```python
def solve_xxx(network: RoadNetwork, W: np.ndarray,      # W: N × |L| travel time samples
              origin: int, destination: int, tau: float, # tau: deadline
              ...) -> dict:
    return {
        "path_x": np.ndarray,         # binary edge selection (|L|,)
        "lateness_count": int,        # late samples count
        "punctuality_prob": float,    # 1 - lateness_count/N
        "status": str,               # "Optimal" / "NoPath" / "SolverError: ..."
        "solve_time": float,         # wall-clock seconds
    }
```

## 9. Report Inventory

| # | Report | Network | Key Result |
|---|--------|---------|------------|
| 01 | 01_initial_65node | Artificial | N=100, CBC, CV low (0.25) |
| 02 | 02_n500_solver_compare | Artificial | N=500, HiGHS vs CBC |
| 03 | 03_audit_seed42 | Artificial | Found CV=0.25 root cause |
| 04 | 04_seed42_final | Artificial | CV=0.54, path-match fix |
| 05 | 05_project_status | — | First full project audit |
| 06 | 06_seed42_highvar | Artificial | CV=0.83, path-match only |
| 07 | 07_seed42_tightM | Artificial | Tight big-M validation (**note:** MILP=78.3% from 2 repeats, biased) |
| 08 | 08_beijing | Beijing | First Beijing run (old CV=0.54) |
| 09 | 09_seed42_audit_fix | Artificial | **Definitive artificial** (Phase 8, full metrics) |
| 10 | 10_beijing_audit_fix | Beijing | **Definitive Beijing** old CV (Phase 8, full metrics) |
| 11 | 11_project_audit | — | Comprehensive audit (4 issues found) |
| 12 | 12_beijing_highvar | Beijing | **High-CV Beijing** (0.775, Phase 9 complete) |
| 13 | 13_maintenance_followup | — | Maintenance alignment, metadata traceability, next-task ordering |
| 14 | 14_deadline_protocol_audit | — | small dataset protocol audit: heuristic vs exact deadline |
| 15 | 15_full_seed42_notebook_rerun | Artificial | full/seed42 notebook + SCIP rerun |
| 16 | 16_full_seed42_detailed_review | Artificial | detailed metrics review, follow-up plan, project status audit |
| 17 | 17_full_protocol_seed42_1000jobs | Artificial | 1000-job large-scale validation on full seed42 |

**Latest result reports in this repo:** 16/17 (artificial), 12 (Beijing high-CV).

Open `docs/report/index.html` for a navigable index with evolution table.

## 10. Known Issues & Gotchas

1. **Report 07 MILP bias** — MILP=78.3% based on only 2 repeats; report 09's 63.7% is the later result from 3 repeats. Keep the numbered report immutable; explain the caveat in later maintenance docs.
2. **ILP α=0.5 time limit hits** — On Beijing with α=0.5, ILP can hit the 120s time limit. Always returns the best feasible solution (verified Optimal in report 12).

## 11. What Changed Since Last Handover (001)

| Change | Detail |
|--------|--------|
| Beijing high-CV experiment | **Done.** CV=0.775, ILP 100%, Dijkstra 71.1%, MILP 68.9% |
| Report 12 | New HTML report for Beijing high-CV results |
| Jupyter notebook | `experiment.ipynb` — 32 cells, replicate run.py workflow |
| Documentation normalization | README doc structure, CLAUDE.md rules, todo.md moved to docs/ |
| Git hygiene | Removed redundant `Cao_SOTA_MP/.gitignore`, added `cache/` to parent |
| Report index | Updated: 17 reports, including detailed rerun review and 1000-job validation |
| Visualization / tests / PuLP | Fig.2-style plots upgraded, deadline tests added, PuLP warning workaround complete |

## 12. Pending Work (Priority Order)

### Medium
- **Metric policy update** — Use tie-aware as the default accuracy headline in summaries and plots; keep path-match as structural diagnostic
- **Threshold sensitivity** — Compare `1/N` with one stricter global tolerance before changing the default rule
- **Multi-seed significance** — Only if a paper-grade statistical section is needed

### Low
- T-Drive real GPS trajectory data integration (optional, needs data acquisition)

## 13. Troubleshooting

1. **Tests fail** → `uv run pytest Cao_SOTA_MP/tests/ -v`. `test_ilp_returns_optimal` verifies ILP vs enumeration — if this fails, solver logic is wrong.
2. **SCIP not found** → `uv sync`. pyscipopt needs SCIP system libraries.
3. **Beijing experiment hangs** → ILP on α=0.5 with 587 nodes can hit 120s limit. Expected — solver returns best feasible.
4. **Memory issues** → Large candidate pools (1000 paths × 500 samples). Reduce `max_paths` in config.
5. **Regenerating data** → `data/generate.py` overwrites cleanly. Network topology is deterministic per seed.
6. **Notebook kernel** → Select the RSP-level `.venv` as kernel in VS Code.

## 14. Key Concepts

| Term | Meaning |
|------|---------|
| **W** | N × \|L\| matrix of travel time samples (N scenarios, \|L\| edges) |
| **τ (tau)** | Deadline: τ = T_min + α·(T_max - T_min) |
| **T_max** | Minimax path time: min over paths of max sample time on that path |
| **α (alpha)** | Deadline tightness: 0.5 (tight) → 0.9 (loose) |
| **ιᵢ (iota)** | Binary: 1 if path exceeds τ in sample i, else 0 |
| **big-M** | Per-sample tight: Mᵢ = max(1, ΣⱼW[i,j]-τ) |
| **Mx = b** | Flow conservation: incidence matrix × edge selection = OD vector |
| **objective_gap** | p_ILP - p_method |
| **tie_aware_correct** | True when \|gap\| ≤ 1/N (within sampling error) |
| **CV** | Coefficient of variation = std/mean per edge |

## 15. Reference Documents

| Document | Path | Purpose |
|----------|------|---------|
| Paper | `docs/2020-Cao-SOTA-MP.pdf` | Original Cao et al. (2020) |
| Spec | `docs/spec.md` | Primary interfaces, algorithms, acceptance criteria |
| Plan | `docs/plan.md` | Phases, key decisions, report inventory |
| Changelog | `docs/change.md` | Chronological, newest-first |
| TODO | `docs/todo.md` | Tasks + completed history + quick commands |
| Report index | `docs/report/index.html` | 17 reports with evolution table |
| CLAUDE.md | `../CLAUDE.md` | AI assistant instructions (RSP level) |
| Handover 001 | `docs/handover/001-project-handover.md` | Previous handover (2026-05-23) |
