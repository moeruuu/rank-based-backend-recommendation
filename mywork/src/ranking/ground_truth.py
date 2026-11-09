"""Build independent ranking labels from measured noise-simulation results."""
from pathlib import Path
import pandas as pd


def build_ground_truth(summary: pd.DataFrame) -> pd.DataFrame:
    required = {"circuit_id", "backend_name", "mean_fidelity", "mean_tvd", "runs"}
    if not required.issubset(summary.columns):
        raise ValueError(f"Missing columns: {required - set(summary.columns)}")
    if summary.duplicated(["circuit_id", "backend_name"]).any():
        raise ValueError("Duplicate circuit/backend pairs")
    if summary.empty or summary[list(required & {"mean_fidelity", "mean_tvd", "runs"})].isna().any().any():
        raise ValueError("Missing measurements")
    if not summary["mean_fidelity"].between(0, 1).all():
        raise ValueError("Fidelity out of range")
    if (summary["runs"] <= 0).any():
        raise ValueError("Runs must be positive")
    # Deterministic ordering, so equal scores do not produce unstable labels.
    gt = summary.sort_values(["circuit_id", "mean_fidelity", "mean_tvd", "backend_name"],
                             ascending=[True, False, True, True]).copy()
    gt["ground_truth_rank"] = gt.groupby("circuit_id").cumcount() + 1
    gt["ground_truth_relevance"] = gt["mean_fidelity"]
    return gt.reset_index(drop=True)


def save_ground_truth(summary_path="data/results/noise_simulation_summary.csv",
                      output_path="data/results/ground_truth.csv"):
    gt = build_ground_truth(pd.read_csv(summary_path))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gt.to_csv(output_path, index=False)
    return gt
