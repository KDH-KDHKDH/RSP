"""Result objects for the public RSP SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd


@dataclass
class RSPCaseResult:
    """Result for a single repeat/OD/alpha case."""

    tau: float
    ilp: dict[str, Any] | None = None
    milp: dict[str, Any] | None = None
    dijkstra: dict[str, Any] | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class RSPResult:
    """Tabular result wrapper with stable public accessors."""

    df: pd.DataFrame
    config: Any | None = None
    dataset_meta: dict[str, Any] = field(default_factory=dict)
    deadline_diagnostics: dict[str, Any] | None = None

    def to_dataframe(self) -> pd.DataFrame:
        return self.df.copy()

    def save_csv(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.df.to_csv(path, index=False)

    def summary(self) -> pd.DataFrame:
        """Return a compact method-level summary using stable SDK names."""
        if self.df.empty:
            return pd.DataFrame()

        grouped = self.df.groupby("method", dropna=False)
        rows = []
        for method, group in grouped:
            row = {
                "method": method,
                "mean_punctuality_prob": group["punctuality_prob"].mean()
                if "punctuality_prob" in group
                else None,
                "mean_solve_time_s": group["solve_time"].mean()
                if "solve_time" in group
                else None,
                "optimal_rate": (group["status"] == "Optimal").mean()
                if "status" in group
                else None,
                "reference_available_rate": group["reference_available"].mean()
                if "reference_available" in group
                else None,
            }
            if "tie_aware_correct" in group:
                row["tie_aware_accuracy"] = group["tie_aware_correct"].mean()
            if "correct" in group:
                row["path_match_accuracy"] = group["correct"].mean()
            if "objective_gap" in group:
                row["mean_objective_gap"] = group["objective_gap"].mean()
            rows.append(row)
        return pd.DataFrame(rows)

    def accuracy(self, metric: str = "tie_aware") -> pd.DataFrame:
        metric_map = {
            "tie_aware": "tie_aware_correct",
            "path_match": "correct",
        }
        column = metric_map.get(metric, metric)
        if column not in self.df:
            raise ValueError(f"Unknown accuracy metric or missing column: {metric}")
        return (
            self.df.groupby("method", dropna=False)[column]
            .mean()
            .reset_index(name=f"{metric}_accuracy")
        )

    def method_comparison(self, reference: str = "ILP") -> pd.DataFrame:
        """Return method-vs-reference rows aligned by case."""
        required = {"repeat", "od_idx", "alpha", "method", "punctuality_prob", "status"}
        self._require_columns(required, "method_comparison")

        index_cols = ["repeat", "od_idx", "alpha"]
        refs = self.df[self.df["method"] == reference].set_index(index_cols)
        methods = self.df[self.df["method"] != reference].set_index(index_cols)
        common = methods.index.intersection(refs.index)
        rows = []
        for idx in common:
            ref_row = refs.loc[idx]
            if isinstance(ref_row, pd.DataFrame):
                ref_row = ref_row.iloc[0]
            method_rows = methods.loc[[idx]]
            for _, method_row in method_rows.iterrows():
                method_prob = method_row.get("punctuality_prob")
                reference_prob = ref_row.get("punctuality_prob")
                gap = (
                    reference_prob - method_prob
                    if pd.notna(reference_prob) and pd.notna(method_prob)
                    else pd.NA
                )
                rows.append(
                    {
                        "repeat": idx[0],
                        "od_idx": idx[1],
                        "alpha": idx[2],
                        "origin": method_row.get("origin"),
                        "dest": method_row.get("dest", method_row.get("destination")),
                        "method": method_row["method"],
                        "reference": reference,
                        "method_punctuality_prob": method_prob,
                        "reference_punctuality_prob": reference_prob,
                        "objective_gap": method_row.get("objective_gap", gap),
                        "computed_gap": gap,
                        "tie_aware_correct": method_row.get("tie_aware_correct"),
                        "path_match_correct": method_row.get("correct"),
                        "method_status": method_row.get("status"),
                        "reference_status": ref_row.get("status"),
                        "reference_available": method_row.get("reference_available"),
                    }
                )
        return pd.DataFrame(rows)

    def solve_time(self) -> pd.DataFrame:
        """Return method-level solve-time summary."""
        self._require_columns({"method", "solve_time"}, "solve_time")
        return (
            self.df.groupby("method", dropna=False)["solve_time"]
            .agg(
                mean_solve_time_s="mean",
                median_solve_time_s="median",
                max_solve_time_s="max",
                min_solve_time_s="min",
            )
            .reset_index()
        )

    def status_counts(self) -> pd.DataFrame:
        """Return per-method solver status counts and rates."""
        self._require_columns({"method", "status"}, "status_counts")
        counts = (
            self.df.groupby(["method", "status"], dropna=False)
            .size()
            .reset_index(name="count")
        )
        totals = counts.groupby("method", dropna=False)["count"].transform("sum")
        counts["rate"] = counts["count"] / totals
        return counts

    def objective_gaps(self) -> pd.DataFrame:
        """Return method-level objective gap summary."""
        self._require_columns({"method", "objective_gap"}, "objective_gaps")
        return (
            self.df.groupby("method", dropna=False)["objective_gap"]
            .agg(
                mean_objective_gap="mean",
                median_objective_gap="median",
                max_objective_gap="max",
                min_objective_gap="min",
            )
            .reset_index()
        )

    def by_alpha(self) -> pd.DataFrame:
        """Return method metrics grouped by alpha."""
        self._require_columns({"alpha", "method"}, "by_alpha")
        return self._grouped_summary(["alpha", "method"])

    def by_od(self) -> pd.DataFrame:
        """Return method metrics grouped by OD pair."""
        self._require_columns({"od_idx", "method"}, "by_od")
        group_cols = ["od_idx", "method"]
        return self._grouped_summary(group_cols)

    def save_figures(self, path: str | Path) -> None:
        """Save a minimal SDK accuracy-by-alpha figure."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        if self.df.empty or not {"alpha", "method", "tie_aware_correct"}.issubset(self.df.columns):
            return

        data = (
            self.df.groupby(["alpha", "method"], dropna=False)["tie_aware_correct"]
            .mean()
            .reset_index(name="tie_aware_accuracy")
        )
        fig, ax = plt.subplots(figsize=(7, 4))
        for method, group in data.groupby("method", dropna=False):
            ax.plot(
                group["alpha"],
                group["tie_aware_accuracy"],
                marker="o",
                label=str(method),
            )
        ax.set_xlabel("alpha")
        ax.set_ylabel("tie_aware_accuracy")
        ax.set_ylim(0, 1.05)
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(path / "tie_aware_accuracy_vs_alpha.png", dpi=160)
        plt.close(fig)

    def worst_cases(self, method: str = "MILP", baseline: str = "Dijkstra") -> pd.DataFrame:
        """Return cases where method punctuality is lower than baseline."""
        required = {"repeat", "od_idx", "alpha", "method", "punctuality_prob"}
        if not required.issubset(self.df.columns):
            missing = sorted(required - set(self.df.columns))
            raise ValueError(f"Missing required columns for worst_cases: {missing}")

        index_cols = ["repeat", "od_idx", "alpha"]
        lhs = self.df[self.df["method"] == method].set_index(index_cols)
        rhs = self.df[self.df["method"] == baseline].set_index(index_cols)
        common = lhs.index.intersection(rhs.index)
        bad = lhs.loc[common, "punctuality_prob"] < rhs.loc[common, "punctuality_prob"]
        bad_index = bad[bad].index
        return self.df.set_index(index_cols).loc[bad_index].reset_index()

    def _grouped_summary(self, group_cols: list[str]) -> pd.DataFrame:
        grouped = self.df.groupby(group_cols, dropna=False)
        rows = []
        for keys, group in grouped:
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = dict(zip(group_cols, keys))
            if "punctuality_prob" in group:
                row["mean_punctuality_prob"] = group["punctuality_prob"].mean()
            if "solve_time" in group:
                row["mean_solve_time_s"] = group["solve_time"].mean()
            if "status" in group:
                row["optimal_rate"] = (group["status"] == "Optimal").mean()
            if "reference_available" in group:
                row["reference_available_rate"] = group["reference_available"].mean()
            if "tie_aware_correct" in group:
                row["tie_aware_accuracy"] = group["tie_aware_correct"].mean()
            if "correct" in group:
                row["path_match_accuracy"] = group["correct"].mean()
            if "objective_gap" in group:
                row["mean_objective_gap"] = group["objective_gap"].mean()
            rows.append(row)
        return pd.DataFrame(rows)

    def _require_columns(self, columns: set[str], caller: str) -> None:
        missing = sorted(columns - set(self.df.columns))
        if missing:
            raise ValueError(f"Missing required columns for {caller}: {missing}")
