"""Configuration objects for the public RSP SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


SUPPORTED_METHODS = {"ILP", "MILP", "Dijkstra"}
SUPPORTED_DEADLINE_MODES = {"heuristic", "exact"}


@dataclass(frozen=True)
class RSPConfig:
    """Typed configuration for SDK experiment runs."""

    methods: tuple[str, ...] = ("ILP", "MILP", "Dijkstra")
    alphas: tuple[float, ...] = (0.5, 0.7, 0.9)
    num_repeats: int | None = None
    num_od_pairs: int | None = None
    solver_backend: str = "SCIP"
    big_m: float = 1_000_000
    time_limit: int = 60
    deadline_mode: str = "heuristic"
    deadline_enumeration_cutoff: int = 15
    max_candidate_paths: int = 1000
    random_seed: int = 42
    data_dir: str | None = None
    num_samples: int | None = None
    output_dir: str | None = None
    save_figures: bool = False
    save_csv: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        methods = tuple(self.methods)
        invalid_methods = set(methods) - SUPPORTED_METHODS
        if invalid_methods:
            raise ValueError(f"Unsupported methods: {sorted(invalid_methods)}")
        if not methods:
            raise ValueError("At least one method must be configured")
        object.__setattr__(self, "methods", methods)

        alphas = tuple(float(alpha) for alpha in self.alphas)
        if not alphas:
            raise ValueError("At least one alpha must be configured")
        for alpha in alphas:
            if not 0.0 <= alpha <= 1.0:
                raise ValueError(f"Alpha must be in [0, 1], got {alpha}")
        object.__setattr__(self, "alphas", alphas)

        for name in ("num_repeats", "num_od_pairs", "num_samples"):
            value = getattr(self, name)
            if value is not None and int(value) <= 0:
                raise ValueError(f"{name} must be None or a positive integer")
            if value is not None:
                object.__setattr__(self, name, int(value))

        if self.deadline_mode not in SUPPORTED_DEADLINE_MODES:
            raise ValueError(
                f"deadline_mode must be one of {sorted(SUPPORTED_DEADLINE_MODES)}, "
                f"got {self.deadline_mode!r}"
            )
        if self.deadline_enumeration_cutoff <= 0:
            raise ValueError("deadline_enumeration_cutoff must be positive")
        if self.max_candidate_paths <= 0:
            raise ValueError("max_candidate_paths must be positive")
        if self.time_limit <= 0:
            raise ValueError("time_limit must be positive")
        if self.big_m <= 0:
            raise ValueError("big_m must be positive")

    @classmethod
    def from_yaml(cls, path: str | Path) -> "RSPConfig":
        """Load an SDK config from the project YAML layout."""
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RSPConfig":
        """Create config from either nested project YAML or flat SDK fields."""
        data_cfg = raw.get("data", {})
        exp_cfg = raw.get("experiment", {})
        solver_cfg = raw.get("solver", {})
        output_cfg = raw.get("output", {})
        candidate_cfg = raw.get("candidate_paths", {})
        deadline_cfg = raw.get("deadline", {})
        network_cfg = raw.get("network", {})

        known_sections = {
            "data",
            "experiment",
            "solver",
            "output",
            "candidate_paths",
            "deadline",
            "network",
        }
        extra = {k: v for k, v in raw.items() if k not in known_sections}

        return cls(
            methods=tuple(exp_cfg.get("methods", raw.get("methods", ("ILP", "MILP", "Dijkstra")))),
            alphas=tuple(exp_cfg.get("alphas", raw.get("alphas", (0.5, 0.7, 0.9)))),
            num_repeats=exp_cfg.get("num_repeats", raw.get("num_repeats")),
            num_od_pairs=exp_cfg.get("num_od_pairs", raw.get("num_od_pairs")),
            solver_backend=solver_cfg.get("backend", raw.get("solver_backend", "SCIP")),
            big_m=solver_cfg.get("big_m", raw.get("big_m", 1_000_000)),
            time_limit=solver_cfg.get("time_limit", raw.get("time_limit", 60)),
            deadline_mode=deadline_cfg.get("mode", raw.get("deadline_mode", "heuristic")),
            deadline_enumeration_cutoff=deadline_cfg.get(
                "enumeration_cutoff",
                raw.get("deadline_enumeration_cutoff", 15),
            ),
            max_candidate_paths=candidate_cfg.get("max_paths", raw.get("max_candidate_paths", 1000)),
            random_seed=network_cfg.get("seed", raw.get("random_seed", 42)),
            data_dir=data_cfg.get("dir", raw.get("data_dir")),
            num_samples=data_cfg.get("num_samples", raw.get("num_samples")),
            output_dir=output_cfg.get("dir", raw.get("output_dir")),
            save_figures=output_cfg.get("save_figures", raw.get("save_figures", False)),
            save_csv=output_cfg.get("save_csv", raw.get("save_csv", False)),
            extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical nested YAML-compatible representation."""
        return {
            "data": {
                "dir": self.data_dir,
                "num_samples": self.num_samples,
            },
            "experiment": {
                "methods": list(self.methods),
                "num_repeats": self.num_repeats,
                "num_od_pairs": self.num_od_pairs,
                "alphas": list(self.alphas),
            },
            "solver": {
                "backend": self.solver_backend,
                "big_m": self.big_m,
                "time_limit": self.time_limit,
            },
            "output": {
                "dir": self.output_dir,
                "save_figures": self.save_figures,
                "save_csv": self.save_csv,
            },
            "candidate_paths": {
                "max_paths": self.max_candidate_paths,
            },
            "deadline": {
                "mode": self.deadline_mode,
                "enumeration_cutoff": self.deadline_enumeration_cutoff,
            },
            "network": {
                "seed": self.random_seed,
            },
            **self.extra,
        }

    def to_yaml(self, path: str | Path) -> None:
        """Write this config to a YAML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.to_dict(), f, sort_keys=False)

    @property
    def expected_job_count(self) -> int | None:
        """Return configured repeat x OD x alpha count when fully specified."""
        if self.num_repeats is None or self.num_od_pairs is None:
            return None
        return self.num_repeats * self.num_od_pairs * len(self.alphas)
