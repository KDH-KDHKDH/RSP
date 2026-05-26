# 004 Delivery Handover — Cao SOTA MP

**Date:** 2026-05-26  
**Purpose:** final delivery-facing handover for the next person or agent  
**Primary status:** core reproduction complete; conflict-graph extensions complete; Beijing conflict extension complete to 300 jobs; current remaining work is explanation and audit, not solver implementation

---

## 1. What To Read First

Read these in order:

1. `README.md`
2. `docs/handover/004-delivery-handover.md`
3. `docs/plan.md`
4. `docs/todo.md`
5. `docs/spec.md`
6. `docs/report/index.html`

Then read these reports only:

- `docs/report/17_full_protocol_seed42_1000jobs.html`
- `docs/report/19_conflict_graph_seed524.html`
- `docs/report/21_beijing_conflict_300jobs.html`

Everything else under `docs/report/` is historical evidence. Keep it, but do not require it as first-pass onboarding material.

---

## 2. Delivery Scope

### Included and important

- `src/` core solver and experiment code
- `run.py` CLI experiment entry
- `experiment.ipynb` interactive entry, saved without trusted result outputs
- `data/full/seed42/`
- `data/full/seed524/`
- `data/beijing/`
- `data/beijing_conflict/`
- `results/full_protocol_seed42_scip/`
- `results/conflict_seed524_scip/`
- `results/beijing_conflict_scip/`
- `docs/` maintenance docs, handovers, and reports

### Included but secondary

- `docs/handover/001-project-handover.md`
- `docs/handover/002-project-handover.md`
- `docs/handover/003-project-handover.md`
- early reports `01` through `16`
- `docs/2020-Cao-SOTA-MP.pdf`
- `docs/paper.html`

These should be treated as archive material, not the primary delivery path.

---

## 3. Audit Summary

### Code status

- `ILP`, `MILP`, and `Dijkstra` implementations are present and aligned with the intended project formulation.
- `deadline.mode = heuristic / exact` support is present.
- strict `0.5/N` tie-aware logic has been removed from active code paths.
- conflict-graph edge typing for both artificial and Beijing datasets is serialized through `network.npz` and survives reload.

### Path status

- CLI paths in `run.py` resolve relative configs and data directories correctly from repo root usage.
- dataset directories `data/full/seed42`, `data/full/seed524`, `data/beijing`, and `data/beijing_conflict` all load successfully through `load_experiment_data`.
- `experiment.ipynb` is the preferred interactive entry, but it should only be treated as a launcher/config surface unless its outputs are freshly regenerated.

### Test status

- `14/14` tests pass under `uv`.

Command used:

```bash
env UV_CACHE_DIR=/tmp/uv-cache uv run pytest Cao_SOTA_MP/tests/ -v
```

---

## 4. Current Meaningful Results

### Artificial baseline

Use report `17`.

- ILP path-match `100%`
- MILP tie-aware `90.2%`
- Dijkstra tie-aware `88.3%`

### Artificial conflict graph

Use report `19`.

- MILP tie-aware `91.2%`
- Dijkstra tie-aware `87.3%`
- conflict structure changes solver behavior materially

### Beijing conflict extension

Use report `21`.

- `300 jobs`
- ILP all optimal
- MILP tie-aware `84.3%`
- Dijkstra tie-aware `67.7%`
- main takeaway: the structured Beijing conflict variance setup appears to widen MILP's advantage over Dijkstra under the primary tie-aware metric

This is the current headline result, but it is still an **explanation-incomplete** result, not a finished mechanism proof.

---

## 5. Current Known Limits

These are the main unresolved items at delivery time:

1. Beijing original-vs-conflict baseline comparison is still missing as one direct table.
2. Conflict OD vs non-conflict OD evidence is still missing.
3. Stable/volatile edge-share evidence in selected paths is still missing.
4. Recent report prose is stronger than the evidence in a few places; use `report 21` as a result summary, not as final causal proof.
5. `experiment.ipynb` saved outputs have been cleared to avoid stale evidence; rerun before citing notebook cells as results.

---

## 6. What Not To Do Next

Do not prioritize:

- solver rewrites
- new threshold variants
- >300-job Beijing expansions
- more report writing before baseline/mechanism evidence is added

---

## 7. Recommended Next Steps

In order:

1. Build one direct Beijing baseline-vs-conflict comparison table
2. Add conflict OD vs non-conflict OD split
3. Add stable/volatile edge-share analysis for chosen paths
4. Regenerate notebook outputs only after the above is settled
5. Then decide whether low-`alpha` Beijing follow-up is worth doing

---

## 8. Minimal Run Commands

```bash
cd /home/kkk/projects/RSP

uv run python Cao_SOTA_MP/data/generate.py --preset conflict --seed 524
uv run python Cao_SOTA_MP/data/generate.py --preset beijing-conflict

uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/beijing.yaml --data-dir Cao_SOTA_MP/data/beijing_conflict --plot

env UV_CACHE_DIR=/tmp/uv-cache uv run pytest Cao_SOTA_MP/tests/ -v
```
