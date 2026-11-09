"""Per-circuit and macro-average ranking evaluation with strict candidate validation."""
from pathlib import Path
import pandas as pd
from src.ranking.metrics import evaluate_ranking


def evaluate_predictions(gt: pd.DataFrame, predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    for column in ("circuit_id", "backend_name", "ground_truth_rank", "ground_truth_relevance"):
        if column not in gt:
            raise ValueError(f"Missing ground truth column: {column}")
    for column in ("circuit_id", "backend_name", "predicted_rank"):
        if column not in predictions:
            raise ValueError(f"Missing prediction column: {column}")
    if gt.empty or predictions.empty:
        raise ValueError("Empty ground truth or predictions")
    if gt.duplicated(["circuit_id", "backend_name"]).any() or predictions.duplicated(["circuit_id", "backend_name"]).any():
        raise ValueError("Duplicate candidates")
    if set(gt["circuit_id"]) != set(predictions["circuit_id"]):
        raise ValueError("Circuit coverage differs between ground truth and predictions")
    result = []
    for circuit_id, g in gt.groupby("circuit_id", sort=True):
        p = predictions[predictions["circuit_id"] == circuit_id]
        if set(g.backend_name) != set(p.backend_name):
            raise ValueError(f"Candidate mismatch for {circuit_id}")
        if (sorted(g.ground_truth_rank.astype(int)) != list(range(1, len(g) + 1)) or
            sorted(p.predicted_rank.astype(int)) != list(range(1, len(p) + 1))):
            raise ValueError("Ranks must be consecutive 1..N")
        actual = g.sort_values("ground_truth_rank").backend_name.tolist()
        predicted = p.sort_values("predicted_rank").backend_name.tolist()
        relevance = dict(zip(g.backend_name, g.ground_truth_relevance))
        result.append({"circuit_id": circuit_id, "num_backends": len(actual),
                       **evaluate_ranking(actual, predicted, relevance)})
    details = pd.DataFrame(result)
    metric_cols = [c for c in details if c not in ("circuit_id", "num_backends")]
    aggregate = pd.DataFrame([{"num_circuits": len(details), **details[metric_cols].mean().to_dict()}])
    return details, aggregate


def save_evaluation(gt_path="data/results/ground_truth.csv",
                    predictions_path="data/results/baseline_predictions.csv",
                    output_dir="data/results"):
    details, aggregate = evaluate_predictions(pd.read_csv(gt_path), pd.read_csv(predictions_path))
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    details.to_csv(out / "ranking_metrics_per_circuit.csv", index=False)
    aggregate.to_csv(out / "ranking_metrics_summary.csv", index=False)
    return details, aggregate
