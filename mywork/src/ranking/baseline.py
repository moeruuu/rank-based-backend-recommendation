"""Calibration-only heuristic recommender: does not read ground-truth simulation scores."""
from pathlib import Path
import numpy as np
import pandas as pd


def predict_from_calibration(features: pd.DataFrame, qubits: pd.DataFrame,
                             gates: pd.DataFrame, backends: pd.DataFrame) -> pd.DataFrame:
    for col in ("circuit_id", "num_qubits", "single_qubit_gates", "two_qubit_gates"):
        if col not in features:
            raise ValueError(f"Missing circuit feature {col}")
    summary = qubits.groupby("backend_name", as_index=False).agg(
        readout_error=("readout_error", "mean"), t1=("t1_seconds", "mean"),
        t2=("t2_seconds", "mean"))
    one = gates[gates["qubits"].astype(str).str.count(",") == 0].groupby("backend_name")["gate_error"].mean()
    two = gates[gates["qubits"].astype(str).str.count(",") == 1].groupby("backend_name")["gate_error"].mean()
    summary["one_qubit_error"] = summary["backend_name"].map(one)
    summary["two_qubit_error"] = summary["backend_name"].map(two)
    summary = summary.merge(backends[["backend_name", "num_qubits"]], on="backend_name", validate="one_to_one")
    rows = []
    for _, circuit in features.iterrows():
        for _, device in summary.iterrows():
            n = int(circuit["num_qubits"])
            if n > int(device["num_qubits"]):
                continue
            # Crude independent reliability heuristic; ignores topology/layout and duration.
            p1 = float(device["one_qubit_error"])
            p2 = float(device["two_qubit_error"])
            pr = float(device["readout_error"])
            if not all(np.isfinite(x) and 0 <= x <= 1 for x in (p1, p2, pr)):
                raise ValueError("Invalid calibration error values")
            score = ((1 - p1) ** int(circuit["single_qubit_gates"]) *
                     (1 - p2) ** int(circuit["two_qubit_gates"]) * (1 - pr) ** n)
            rows.append({"circuit_id": circuit["circuit_id"], "backend_name": device["backend_name"],
                         "predicted_score": float(score)})
    if not rows:
        raise ValueError("No compatible circuit/backend pairs")
    df = pd.DataFrame(rows).sort_values(["circuit_id", "predicted_score", "backend_name"],
                                        ascending=[True, False, True]).reset_index(drop=True)
    df["predicted_rank"] = df.groupby("circuit_id").cumcount() + 1
    return df


def save_baseline(calibration_dir="data/calibration", circuits_dir="data/circuits",
                  output_path="data/results/baseline_predictions.csv"):
    cd = Path(calibration_dir)
    df = predict_from_calibration(
        pd.read_csv(Path(circuits_dir) / "circuit_features.csv"),
        pd.read_csv(cd / "qubit_calibration.csv"),
        pd.read_csv(cd / "gate_calibration.csv"),
        pd.read_csv(cd / "backend_summary.csv"))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    return df
