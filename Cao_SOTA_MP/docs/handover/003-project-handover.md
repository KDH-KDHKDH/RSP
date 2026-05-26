# 003 Project Handover — Cao SOTA MP

**Date:** 2026-05-26  
**Status:** Core reproduction complete. Artificial conflict-graph experiment complete. Beijing conflict experiment extended to 300 jobs. Current work is audit/maintenance driven, with emphasis on mechanism evidence and report tightening.  
**Tests:** 14/14 passing at last check.  
**Previous handover:** 002 (2026-05-24)

---

## 1. What This Project Is

This project reproduces the ILP exact solution for the reliable shortest path / punctuality problem from **Cao et al. (2020)**.

Three methods are implemented:

- `ILP`: exact solution for minimizing late-sample count
- `MILP`: L1-relaxation baseline
- `Dijkstra`: mean-shortest-path baseline

The project now has three experiment families:

1. Original artificial network (`seed42`)
2. Artificial conflict graph (`seed524`)
3. Beijing OSM network, including a multi-level conflict-variance extension

---

## 2. Current State

### Stable and already reproduced

- Artificial `seed42` high-variance experiment is stable
- Beijing high-variance baseline experiment is stable
- `deadline.mode = heuristic / exact` protocol support is implemented
- `tie-aware accuracy` is the primary comparison metric
- Default tie-aware rule is fixed to `|gap| ≤ 1/N`
- Notebook-first workflow is established through `experiment.ipynb`

### Recently completed

- Report 19: conflict graph (`seed524`)
- Report 20: Beijing multi-level conflict variance preliminary run (`100 jobs`)
- Report 21: Beijing conflict extension (`300 jobs`)

### Current audit judgment

- The new Beijing conflict results are promising, but not yet fully explained.
- The main gap now is **mechanism evidence**, not more solver work.
- The current notebook output state needs cleanup because its saved outputs do not fully match the latest Beijing conflict run.
- The next step is not “more Beijing jobs”, but a clearer explanation chain:
  baseline comparison -> conflict OD evidence -> path edge-type evidence -> wording cleanup

---

## 3. Most Recent Experimental Conclusions

### Artificial seed42 baseline

Latest stable conclusion:

- `ILP` path-match = `100%`
- `MILP` tie-aware = `90.2%`
- `Dijkstra` tie-aware = `88.3%`

Key interpretation:

- Dijkstra is better on strict path-match
- MILP is better on tie-aware

### Artificial conflict graph (`seed524`)

Latest stable conclusion from report 19:

- Conflict structure successfully changes solver behavior
- `MILP` tie-aware stays above `Dijkstra`
- `MILP` path-match improves materially compared with `seed42`

Open question:

- Need better evidence for *why* MILP improves:
  - conflict OD vs non-conflict OD
  - edge-type mix in selected paths
  - source of MILP gains

### Beijing conflict experiment

Current most important result is report 21:

- `300 jobs` total
- `ILP` all optimal
- `MILP tie-aware = 84.3%`
- `Dijkstra tie-aware = 67.7%`
- gap = `+16.6pp` in favor of MILP

Interpretation that is safe:

- Multi-level variance on Beijing topology appears to widen MILP’s advantage over Dijkstra under tie-aware evaluation

Interpretation that is **not yet safe**:

- “design fully validated”
- “largest separation proves the mechanism”

Because:

- we still need direct Beijing baseline-vs-conflict comparison in one table
- we still need conflict OD / non-conflict OD evidence
- we still need stable/volatile edge-share evidence in chosen paths
- notebook saved outputs still need cleanup

---

## 4. Key Files To Read First

### Core docs

- `docs/plan.md`
- `docs/todo.md`
- `docs/spec.md`
- `docs/change.md`
- `docs/report/index.html`

### Most relevant reports now

- `docs/report/16_full_seed42_detailed_review.html`
- `docs/report/19_conflict_graph_seed524.html`
- `docs/report/20_beijing_conflict_prelim.html`
- `docs/report/21_beijing_conflict_300jobs.html`

### Main experiment entry

- `experiment.ipynb`

### Core code

- `src/experiment.py`
- `src/generator.py`
- `src/visualize.py`
- `src/osm_network.py`

---

## 5. Result Directories Worth Inspecting

### Artificial baseline

- `results/full_protocol_seed42_scip/`

### Artificial conflict graph

- `results/conflict_seed524_scip/`

### Beijing conflict graph

- `results/beijing_conflict_scip/`

Important files inside result dirs:

- `results.csv`
- `compute_time_summary.csv`
- `worst_cases.csv`

When auditing a report, always verify those three before trusting the prose.

---

## 6. Current Open Issues

### 1. Beijing conflict explanation is still incomplete

Need to add:

- baseline Beijing vs conflict Beijing comparison
- conflict OD vs non-conflict OD split
- stable/volatile edge share in chosen paths

### 2. Notebook output drift

`experiment.ipynb` is the preferred entry, but the saved outputs are not fully aligned with the latest Beijing conflict experiment.

At minimum, future cleanup should ensure:

- output cells correspond to current config
- no stale result tables remain
- summary cells run without missing-function errors

### 3. Report tone needs audit discipline

Some recent reports state conclusions more strongly than the evidence supports, especially:

- “historical maximum separation”
- “design validated”

Use softer language until mechanism evidence is added.

---

## 7. Recommended Next Steps

In order:

1. Audit and tighten report 20 / 21 language
2. Add Beijing baseline-vs-conflict comparison
3. Add mechanism evidence for conflict OD and edge-type mix
4. Repair notebook output state
5. Only then decide whether more Beijing runs are needed

Do **not** prioritize:

- more solver tuning
- new threshold variants
- larger Beijing runs before explanation is complete

---

## 8. Working Rules For The Next Person

- Treat `tie-aware accuracy` as the main headline metric
- Keep `path-match` as secondary structural diagnostic
- Keep tie-aware tolerance fixed at `1/N`
- Do not revive complex threshold variants unless explicitly requested
- Do not overwrite existing numbered reports; add new ones
- Prefer audit/maintenance and explanation over new code unless a specific blocker appears
