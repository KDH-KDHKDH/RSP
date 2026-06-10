"""Metric helpers shared by the public SDK facade."""

from __future__ import annotations

import numpy as np


def path_match(path_x: np.ndarray | None, ref_path_x: np.ndarray | None) -> bool | None:
    """Return whether two path selection vectors are exactly identical."""
    if path_x is None or ref_path_x is None:
        return None
    return bool(np.array_equal(path_x, ref_path_x))


def tie_aware_correct(method_prob: float, reference_prob: float, num_samples: int) -> bool:
    """Return whether a probability gap is within one empirical sample."""
    return bool(abs(reference_prob - method_prob) <= 1.0 / num_samples)


def compute_path_stats(W: np.ndarray, path_x: np.ndarray | None, tau: float) -> dict:
    """Compute late count and timing diagnostics for a path vector."""
    if path_x is None:
        return {
            "late_count": None,
            "delay_sum": None,
            "max_delay": None,
            "path_length": None,
            "mean_time": None,
        }
    path_times = W @ path_x
    delays = np.maximum(0, path_times - tau)
    return {
        "late_count": int(np.sum(path_times > tau)),
        "delay_sum": float(np.sum(delays)),
        "max_delay": float(np.max(delays)),
        "path_length": int(np.sum(path_x)),
        "mean_time": float(np.mean(path_times)),
    }
