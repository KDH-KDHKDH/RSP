# RSP: Reliable Shortest Path

Reproduction of **Cao et al. (2020)** — an ILP-based exact solver for finding the path
with maximum probability of arriving on-time under stochastic edge travel times.

## Quick Start

```bash
# Install dependencies
uv sync

# Generate experiment data (preset: small / full)
uv run python Cao_SOTA_MP/data/generate.py --preset small
uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42

# Run experiment
uv run python Cao_SOTA_MP/run.py                                                # small dataset (default)
uv run python Cao_SOTA_MP/run.py --data-dir Cao_SOTA_MP/data/full/seed42 --plot # full dataset with figures

# Run tests
uv run pytest Cao_SOTA_MP/tests/ -v
```

## Solvers

| Solver | File | Description |
|--------|------|-------------|
| **ILP** | `src/ilp_solver.py` | Exact solution via binary lateness indicators + Big-M constraints |
| **MILP** | `src/milp_solver.py` | L1-norm relaxation with continuous penalty variables |
| **Dijkstra** | `src/dijkstra_solver.py` | Mean shortest path baseline |

All solvers take `(network, W, origin, destination, tau)` and return `{path_x, punctuality_prob, status, solve_time}`.

## Current Results

### Artificial Network (65 nodes, 123 edges, CV=0.83, seed=42)

| Method | Path-Match Accuracy | Tie-Aware Accuracy | Solve Time (mean) |
|--------|--------------------|--------------------|--------------------|
| ILP | **100.0%** | **100.0%** | 0.33s |
| Dijkstra | 75.2% | 88.3% | 0.0003s |
| MILP | 63.7% | 90.2% | 0.17s |

### Beijing OSM Network (587 nodes, 1066 edges, CV=0.54, 3 repeats)

| Method | Path-Match Accuracy | Tie-Aware Accuracy | Solve Time (mean) |
|--------|--------------------|--------------------|--------------------|
| ILP | **100.0%** | **100.0%** | 22.2s |
| Dijkstra | 85.6% | 96.7% | 0.005s |
| MILP | 81.1% | 95.6% | 5.2s |

Note: Beijing high-CV data (median 0.775) generated, experiment pending.

ILP = 100% accuracy reproduced. Tie-aware accuracy shows baselines closer to optimal than strict path-matching suggests (objective_gap < 0.001 in both networks).

## Project Structure

```
Cao_SOTA_MP/
├── data/                # Generated datasets (small / full/seed42)
│   └── generate.py      # Data generation entry point (--preset, --seed)
├── configs/             # YAML experiment configs
├── src/                 # Source code (flat package)
│   ├── graph.py         # RoadNetwork + incidence matrix
│   ├── generator.py     # Graph/travel-time generation + deadline
│   ├── ilp_solver.py    # ILP exact solver
│   ├── milp_solver.py   # MILP relaxation
│   ├── dijkstra_solver.py  # Dijkstra baseline
│   ├── experiment.py    # Experiment orchestration
│   └── visualize.py     # Accuracy vs α + scatter plots
├── tests/               # 10 unit tests
├── docs/                # Documentation (plans, specs, changelog, todo, reports)
├── results/             # Experiment outputs (CSV + figures)
└── run.py               # Single experiment entry point
```

## Configuration

Switch datasets via `--data-dir`:

```bash
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/artificial_n500.yaml --data-dir Cao_SOTA_MP/data/full/seed42 --plot
uv run python Cao_SOTA_MP/run.py --config Cao_SOTA_MP/configs/beijing.yaml --data-dir Cao_SOTA_MP/data/beijing --plot
```

## Key Design Decisions

- **ILP is ground-truth** — no path enumeration needed for accuracy evaluation
- **Data generation is separate from solving** — `data/generate.py` produces self-contained directories
- **SCIP solver** (pyscipopt 6.2.1) — open-source, stable (HiGHS has memory corruption bug)
- **Two accuracy metrics**: strict path-vector match + tie-aware (|gap| ≤ 1/N)
- **Per-sample tight big-M** — Mᵢ = max(1, ΣⱼW[i,j]-τ), 200-8000× tighter than fixed 1e6
- **Shared venv** at repo root — managed by `uv` with `pyproject.toml`

## Reports

See `docs/report/index.html` for all 11 experiment reports with detailed analysis.

## Documentation Structure

Each file under `docs/` has a specific purpose and content scope. When modifying the project, update the relevant document(s) as described below.

### `docs/change.md` — Changelog

**Purpose:** Chronological log of every change made to the project.

**Content rules:**
- Each entry is dated (`## [YYYY-MM-DD]`) with a descriptive title
- Newest entries go at the **top** of the file (reverse chronological)
- Describe what changed and why — not just a list of files touched
- Group related changes under a single dated heading
- Keep entries factual and specific: what problem existed, what was done, what the outcome was

### `docs/handover/` — Handover Documents

**Purpose:** Onboarding material for the next person (or agent) taking over the project. A self-contained briefing that lets someone unfamiliar with the project understand its state and start working immediately.

**Content rules:**
- Numbered files (`001-*.md`, `002-*.md`, ...) for sequential handovers
- Must cover: what the project is, current progress, quick-start commands, architecture, key design decisions, known issues, next steps, and a glossary
- Write for a reader with zero prior context — no implicit knowledge, no "as discussed before"
- Keep under 250 lines; prefer links to report files for deep dives
- Update or create a new handover when the project changes hands or reaches a major milestone

### `docs/report/` — Experiment Reports

**Purpose:** Self-contained HTML reports documenting experimental results, project audits, and analysis findings.

**Content rules:**
- Use HTML with embedded CSS for a polished, readable presentation (styled tables, color-coded callouts, clear typography)
- Number files sequentially: `01_<slug>.html`, `02_<slug>.html`, ...
- Maintain `index.html` as a navigable index of all reports with one-line descriptions
- Each report should be understandable standalone: include date, scope, methodology, results, and conclusions
- Use visual hierarchy: colored callout boxes (good/warn/info/highlight) for key findings, tables for data, clear section headers
- Reports are immutable once numbered — if results change, create a new report; do not overwrite

### `docs/plan.md` — Project Plan

**Purpose:** High-level roadmap of phases, goals, and key decisions. Answers "where are we going and why."

**Content rules:**
- Keep phases broad (Phase 1, Phase 2, ...) with clear completion criteria
- Record key design decisions and their rationale (decision + reason table)
- Document the report naming convention and inventory
- Update when phases complete or new directions are decided
- Do NOT list granular daily tasks — that's `todo.md`

### `docs/todo.md` — Current Task List

**Purpose:** Granular, actionable task list derived from the plan. Answers "what do I do next."

**Content rules:**
- Sort by priority: High → Medium → Low
- Each task is a concrete, completable action (checkbox `- [ ]`)
- Include exact shell commands where applicable (copy-paste ready)
- Keep a "Quick Commands" section at the bottom for frequent operations
- Mark completed items with `[x]` and move to a "Done" section or strike through
- Trim aggressively — if a completed task is no longer relevant, delete it

### `docs/spec.md` — Specification

**Purpose:** Defines what "done" means. The authoritative reference for interfaces, algorithms, data formats, acceptance criteria, and technology stack.

**Content rules:**
- Specify all external interfaces (CLI arguments, config format, solver signatures, data file formats)
- Document all algorithm models with mathematical notation (objective functions, constraints, variable domains)
- Define acceptance criteria that are measurable (accuracy ranges, timing budgets)
- Keep in sync with the actual implementation — stale specs mislead
- Update when interfaces, dependencies, or acceptance thresholds change
- Do NOT include implementation details, plans, or TODO items — those belong elsewhere

## References

- Cao, Z., Guo, H., Zhang, J., Niyato, D., & Fastenrath, U. (2020). Finding the Shortest Path with Maximum Punctuality Probability under Stochastic Travel Times. *IEEE Transactions on Intelligent Transportation Systems*.
