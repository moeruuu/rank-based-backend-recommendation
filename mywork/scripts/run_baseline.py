"""Run only calibration-based predictions (no Qiskit installation required)."""
from src.ranking.baseline import save_baseline

if __name__ == "__main__":
    predictions = save_baseline()
    print(f"Generated {len(predictions)} predictions for {predictions.circuit_id.nunique()} circuits")
    print(predictions.to_string(index=False))
