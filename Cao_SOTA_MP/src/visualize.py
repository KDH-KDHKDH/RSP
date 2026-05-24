"""Result visualization — reproduce paper figures."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


METHOD_ORDER = ["ILP", "MILP", "Dijkstra"]
METHOD_STYLE = {
    "ILP": {"color": "#2563eb", "marker": "o"},
    "MILP": {"color": "#dc2626", "marker": "s"},
    "Dijkstra": {"color": "#059669", "marker": "^"},
}


def plot_accuracy_vs_deadline(df: pd.DataFrame, output_dir: str = "results/figures"):
    """Reproduce Fig.2(a): average accuracy for each method vs deadline (alpha).

    Primary chart: tie-aware accuracy (|gap| ≤ 1/N).
    Auxiliary charts: strict threshold (|gap| ≤ 0.5/N) and path-match accuracy.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Primary: Tie-aware accuracy (|gap| ≤ 1/N)
    if "tie_aware_correct" in df.columns and df["tie_aware_correct"].notna().any():
        tie_acc = (
            df.groupby(["alpha", "method"], as_index=False)["tie_aware_correct"]
            .mean()
            .rename(columns={"tie_aware_correct": "accuracy"})
            .sort_values(["method", "alpha"])
        )
        fig, ax = plt.subplots(figsize=(8, 5))
        for method in METHOD_ORDER:
            subset = tie_acc[tie_acc["method"] == method]
            style = METHOD_STYLE[method]
            ax.plot(
                subset["alpha"],
                subset["accuracy"],
                label=method,
                color=style["color"],
                marker=style["marker"],
                linewidth=2.2,
                markersize=7,
            )
        ax.set_xlabel("α (deadline level)")
        ax.set_ylabel("Tie-Aware Accuracy (|gap| ≤ 1/N)")
        ax.set_xticks(sorted(tie_acc["alpha"].unique()))
        ax.set_ylim(0.8, 1.02)
        ax.legend()
        ax.set_title("Tie-Aware Accuracy vs Deadline (primary metric)")
        ax.grid(True, alpha=0.25, linestyle="--", linewidth=0.8)
        fig.tight_layout()
        fig.savefig(f"{output_dir}/accuracy_vs_deadline.png", dpi=150)
        plt.close(fig)
        print(f"  Saved: {output_dir}/accuracy_vs_deadline.png")

    # Strict threshold: Tie-aware accuracy (|gap| ≤ 0.5/N)
    if "tie_aware_correct_strict" in df.columns and df["tie_aware_correct_strict"].notna().any():
        tie_strict_acc = (
            df.groupby(["alpha", "method"], as_index=False)["tie_aware_correct_strict"]
            .mean()
            .rename(columns={"tie_aware_correct_strict": "accuracy"})
            .sort_values(["method", "alpha"])
        )
        fig, ax = plt.subplots(figsize=(8, 5))
        for method in METHOD_ORDER:
            subset = tie_strict_acc[tie_strict_acc["method"] == method]
            style = METHOD_STYLE[method]
            ax.plot(
                subset["alpha"],
                subset["accuracy"],
                label=method,
                color=style["color"],
                marker=style["marker"],
                linewidth=2.2,
                markersize=7,
            )
        ax.set_xlabel("α (deadline level)")
        ax.set_ylabel("Tie-Aware Accuracy (|gap| ≤ 0.5/N)")
        ax.set_xticks(sorted(tie_strict_acc["alpha"].unique()))
        ax.set_ylim(0.55, 1.02)
        ax.legend()
        ax.set_title("Tie-Aware Accuracy vs Deadline (strict threshold |gap| ≤ 0.5/N)")
        ax.grid(True, alpha=0.25, linestyle="--", linewidth=0.8)
        fig.tight_layout()
        fig.savefig(f"{output_dir}/tie_aware_strict_accuracy_vs_deadline.png", dpi=150)
        plt.close(fig)
        print(f"  Saved: {output_dir}/tie_aware_strict_accuracy_vs_deadline.png")

    # Auxiliary: Path-match accuracy
    if "correct" in df.columns and df["correct"].notna().any():
        acc = (
            df.groupby(["alpha", "method"], as_index=False)["correct"]
            .mean()
            .rename(columns={"correct": "accuracy"})
            .sort_values(["method", "alpha"])
        )
        fig, ax = plt.subplots(figsize=(8, 5))
        for method in METHOD_ORDER:
            subset = acc[acc["method"] == method]
            style = METHOD_STYLE[method]
            ax.plot(
                subset["alpha"],
                subset["accuracy"],
                label=method,
                color=style["color"],
                marker=style["marker"],
                linewidth=2.2,
                markersize=7,
            )
        ax.set_xlabel("α (deadline level)")
        ax.set_ylabel("Path-Match Accuracy")
        ax.set_xticks(sorted(acc["alpha"].unique()))
        ax.set_ylim(0.55, 1.02)
        ax.legend()
        ax.set_title("Path-Match Accuracy vs Deadline (auxiliary)")
        ax.grid(True, alpha=0.25, linestyle="--", linewidth=0.8)
        fig.tight_layout()
        fig.savefig(f"{output_dir}/path_match_accuracy_vs_deadline.png", dpi=150)
        plt.close(fig)
        print(f"  Saved: {output_dir}/path_match_accuracy_vs_deadline.png")


def plot_probability_comparison(df: pd.DataFrame, output_dir: str = "results/figures"):
    """Reproduce Fig.2(b)(c): punctuality probability scatter plots."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    key_cols = ["repeat", "od_idx", "origin", "dest", "alpha"]
    ilp_df = (
        df[df["method"] == "ILP"][key_cols + ["punctuality_prob"]]
        .rename(columns={"punctuality_prob": "ilp_prob"})
    )

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    comparisons = [("Dijkstra", axes[0]), ("MILP", axes[1])]

    for method, ax in comparisons:
        method_df = (
            df[df["method"] == method][key_cols + ["punctuality_prob"]]
            .rename(columns={"punctuality_prob": "method_prob"})
        )
        merged = ilp_df.merge(method_df, on=key_cols, how="inner")
        style = METHOD_STYLE[method]

        ax.scatter(
            merged["ilp_prob"],
            merged["method_prob"],
            s=26,
            alpha=0.7,
            color=style["color"],
            edgecolors="none",
        )

        min_prob = min(merged["ilp_prob"].min(), merged["method_prob"].min())
        max_prob = max(merged["ilp_prob"].max(), merged["method_prob"].max())
        lo = max(0.0, min_prob - 0.01)
        hi = min(1.0, max_prob + 0.01)
        ax.plot([lo, hi], [lo, hi], linestyle="--", color="#64748b", linewidth=1.2)
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_xlabel("ILP Punctuality Probability")
        ax.set_ylabel(f"{method} Punctuality Probability")
        ax.set_title(f"ILP vs {method}")
        ax.grid(True, alpha=0.25, linestyle="--", linewidth=0.8)

    fig.tight_layout()
    fig.savefig(f"{output_dir}/probability_comparison.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {output_dir}/probability_comparison.png")


def save_compute_time_table(df: pd.DataFrame, output_dir: str = "results"):
    """Save a paper-style compute-time summary table."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    grouped = (
        df.groupby("method")
        .agg(
            tie_aware_accuracy=("tie_aware_correct", "mean"),
            tie_aware_accuracy_strict=("tie_aware_correct_strict", "mean"),
            path_match_accuracy=("correct", "mean"),
            mean_solve_time_s=("solve_time", "mean"),
            median_solve_time_s=("solve_time", "median"),
            max_solve_time_s=("solve_time", "max"),
        )
        .reindex(METHOD_ORDER)
        .reset_index()
    )

    csv_path = Path(output_dir) / "compute_time_summary.csv"
    grouped.to_csv(csv_path, index=False)
    print(f"  Saved: {csv_path}")


def print_summary(df: pd.DataFrame):
    """Print summary table (like Table I in paper)."""
    print("\n=== Results Summary ===\n")

    if "reference_available" in df.columns:
        ilp_rows = df[df["method"] == "ILP"]
        if not ilp_rows.empty:
            ref_rate = ilp_rows["reference_available"].mean()
            print(f"Reference availability (ILP Optimal): {ref_rate:.1%}")

    if "status" in df.columns:
        print("\nStatus counts by method:")
        status_counts = df.groupby(["method", "status"]).size()
        for (method, status), count in status_counts.items():
            print(f"  {method:10s} {status:12s}: {count}")

    # Tie-aware accuracy (primary metric)
    if "tie_aware_correct" in df.columns and df["tie_aware_correct"].notna().any():
        tie_acc = df.groupby("method")["tie_aware_correct"].mean()
        print("Tie-Aware Accuracy (|gap| ≤ 1/N) — primary metric:")
        for method, a in tie_acc.items():
            print(f"  {method:10s}: {a:.1%}")

    # Tie-aware strict threshold
    if "tie_aware_correct_strict" in df.columns and df["tie_aware_correct_strict"].notna().any():
        tie_strict_acc = df.groupby("method")["tie_aware_correct_strict"].mean()
        print("\nTie-Aware Accuracy (|gap| ≤ 0.5/N) — strict threshold:")
        for method, a in tie_strict_acc.items():
            print(f"  {method:10s}: {a:.1%}")

    # Path-match accuracy (auxiliary diagnostic)
    if "correct" in df.columns and df["correct"].notna().any():
        acc = df.groupby("method")["correct"].mean()
        print("\nPath-Match Accuracy (auxiliary):")
        for method, a in acc.items():
            print(f"  {method:10s}: {a:.1%}")

    # Objective gap
    if "objective_gap" in df.columns and df["objective_gap"].notna().any():
        non_ilp = df[df["method"] != "ILP"]
        gap_stats = non_ilp.groupby("method")["objective_gap"].agg(["mean", "max"])
        print("\nObjective Gap (p_ILP - p_method):")
        for method, row in gap_stats.iterrows():
            print(f"  {method:10s}: mean={row['mean']:.4f} max={row['max']:.4f}")

    # Average solve time
    times = df.groupby("method")["solve_time"].mean()
    print("\nAverage Solve Time (s):")
    for method, t in times.items():
        print(f"  {method:10s}: {t:.4f}")

    # Punctuality probability
    probs = df.groupby("method")["punctuality_prob"].mean()
    print("\nAverage Punctuality Probability:")
    for method, p in probs.items():
        print(f"  {method:10s}: {p:.4f}")
    print()
