"""Data monitoring and drift detection."""

from typing import Any
import numpy as np


def compute_stats(data: list | np.ndarray) -> dict[str, float]:
    """Compute basic statistics for a dataset.

    Args:
        data: Input data (list or numpy array)

    Returns:
        Dictionary of statistics
    """
    if isinstance(data, list):
        data = np.array(data)

    if len(data) == 0:
        return {}

    stats = {
        "count": float(len(data)),
        "mean": float(np.mean(data)),
        "std": float(np.std(data)),
        "min": float(np.min(data)),
        "max": float(np.max(data)),
        "median": float(np.median(data)),
        "q25": float(np.percentile(data, 25)),
        "q75": float(np.percentile(data, 75)),
    }

    return stats


def calculate_psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    """Calculate Population Stability Index (PSI) to detect drift.

    Args:
        expected: Reference distribution
        actual: Current distribution
        buckets: Number of buckets for histogram

    Returns:
        PSI value
    """

    def scale_range(input_array, min_val, max_val):
        input_array += -(np.min(input_array))
        input_array /= np.max(input_array) / (max_val - min_val)
        input_array += min_val
        return input_array

    breakpoints = np.arange(0, buckets + 1) / (buckets) * 100
    breakpoints = np.percentile(expected, breakpoints)

    expected_percents = np.histogram(expected, breakpoints)[0] / len(expected)
    actual_percents = np.histogram(actual, breakpoints)[0] / len(actual)

    def sub_psi(e_perc, a_perc):
        if a_perc == 0:
            a_perc = 0.0001
        if e_perc == 0:
            e_perc = 0.0001

        value = (e_perc - a_perc) * np.log(e_perc / a_perc)
        return value

    psi_value = np.sum([sub_psi(expected_percents[i], actual_percents[i]) for i in range(0, len(expected_percents))])

    return psi_value


def detect_drift(
    reference_data: list | np.ndarray,
    current_data: list | np.ndarray,
    threshold: float = 0.1,
) -> dict[str, Any]:
    """Detect data drift between reference and current data.

    Args:
        reference_data: Reference dataset (e.g. training data)
        current_data: Current dataset (e.g. inference data)
        threshold: PSI threshold for drift warning

    Returns:
        Drift detection result
    """
    if isinstance(reference_data, list):
        reference_data = np.array(reference_data)
    if isinstance(current_data, list):
        current_data = np.array(current_data)

    psi = calculate_psi(reference_data, current_data)

    return {
        "drift_detected": psi > threshold,
        "psi": psi,
        "threshold": threshold,
        "reference_stats": compute_stats(reference_data),
        "current_stats": compute_stats(current_data),
    }
