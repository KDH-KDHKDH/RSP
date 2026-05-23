"""Result visualization — reproduce paper figures."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def plot_accuracy_vs_deadline(df: pd.DataFrame, output_dir: str = "results/figures"):
    """Reproduce Fig.2(a): average accuracy for each method vs deadline (alpha)."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    acc = df.groupby(["alpha", "method"])["correct"].mean().reset_index()
    acc.columns = ["alpha", "method", "accuracy"]

    fig, ax = plt.subplots(figsize=(8, 5))
    for method in ["ILP", "MILP", "Dijkstra"]:
        subset = acc[acc["method"] == method]
        ax.plot(subset["alpha"], subset["accuracy"], "o-", label=method, markersize=8)

    ax.set_xlabel("α (deadline level)")
    ax.set_ylabel("Average Accuracy")
    ax.set_ylim(0, 1.1)
    ax.legend()
    ax.set_title("Accuracy Comparison with Different Deadlines")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{output_dir}/accuracy_vs_deadline.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {output_dir}/accuracy_vs_deadline.png")


def plot_probability_comparison(df: pd.DataFrame, output_dir: str = "results/figures"):
    """Reproduce Fig.2(b)(c): punctuality probability scatter plots."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    ilp_df = df[df["method"] == "ILP"].reset_index(drop=True)
    milp_df = df[df["method"] == "MILP"].reset_index(drop=True)
    dij_df = df[df["method"] == "Dijkstra"].reset_index(drop=True)

    # ILP vs Dijkstra
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax = axes[0]
    n = min(len(ilp_df), len(dij_df), 200)
    ax.scatter(range(n), ilp_df["punctuality_prob"][:n], s=15, label="ILP", alpha=0.7)
    ax.scatter(range(n), dij_df["punctuality_prob"][:n], s=15, label="Dijkstra", alpha=0.7)
    ax.set_xlabel("Test Instance")
    ax.set_ylabel("Punctuality Probability")
    ax.set_title("ILP vs Dijkstra")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # ILP vs MILP
    ax = axes[1]
    n = min(len(ilp_df), len(milp_df), 200)
    ax.scatter(range(n), ilp_df["punctuality_prob"][:n], s=15, label="ILP", alpha=0.7)
    ax.scatter(range(n), milp_df["punctuality_prob"][:n], s=15, label="MILP", alpha=0.7)
    ax.set_xlabel("Test Instance")
    ax.set_ylabel("Punctuality Probability")
    ax.set_title("ILP vs MILP")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(f"{output_dir}/probability_comparison.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {output_dir}/probability_comparison.png")


def print_summary(df: pd.DataFrame):
    """Print summary table (like Table I in paper)."""
    print("\n=== Results Summary ===\n")

    # Accuracy by method (exact path match)
    if "correct" in df.columns and df["correct"].notna().any():
        acc = df.groupby("method")["correct"].mean()
        print("Average Accuracy (exact path match):")
        for method, a in acc.items():
            print(f"  {method:10s}: {a:.1%}")

    # Tie-aware accuracy
    if "tie_aware_correct" in df.columns and df["tie_aware_correct"].notna().any():
        tie_acc = df.groupby("method")["tie_aware_correct"].mean()
        print("\nTie-Aware Accuracy (|gap| <= 1/N):")
        for method, a in tie_acc.items():
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
