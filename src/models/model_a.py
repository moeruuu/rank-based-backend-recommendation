
import json
import math
from pathlib import Path

import pandas as pd
from qiskit import qpy


# ==========================================
# 1. PROJECT PATHS
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GATE_FILE = PROJECT_ROOT / "data/calibration/gate_calibration.csv"
TRANSPILED_DIR = PROJECT_ROOT / "data/transpiled"
OUTPUT_DIR = PROJECT_ROOT / "data/processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "model_a_scores.csv"


# ==========================================
# 2. LOAD CALIBRATION DATA
# ==========================================

def load_gate_calibration():

    df = pd.read_csv(GATE_FILE)

    calibration = {}

    for _, row in df.iterrows():

        qubits = tuple(json.loads(row["qubits"]))

        key = (
            row["backend_name"],
            row["gate_name"],
            qubits
        )

        error = float(row["gate_error"])

        if not 0 <= error < 1:
            raise ValueError(
                f"Invalid gate error: {key} = {error}"
            )

        calibration[key] = error

    return calibration


# ==========================================
# 3. CALCULATE MODEL A SCORE
# ==========================================

def calculate_success_probability(
    circuit,
    backend_name,
    calibration
):

    log_probability = 0.0
    gate_count = 0

    ignored_gates = {
        "barrier",
        "measure",
        "delay"
    }

    for instruction in circuit.data:

        operation = instruction.operation
        gate_name = operation.name

        if gate_name in ignored_gates:
            continue

        physical_qubits = tuple(
            circuit.find_bit(qubit).index
            for qubit in instruction.qubits
        )

        key = (
            backend_name,
            gate_name,
            physical_qubits
        )

        if key not in calibration:
            raise KeyError(
                f"Missing calibration: {key}"
            )

        gate_error = calibration[key]

        # Accumulate log probability to avoid
        # numerical underflow for large circuits.
        log_probability += math.log1p(-gate_error)

        gate_count += 1

    success_probability = math.exp(log_probability)

    return {
        "gate_count": gate_count,
        "log_success_probability": log_probability,
        "success_probability": success_probability
    }


# ==========================================
# 4. LOAD TRANSPILED CIRCUITS
# ==========================================

def load_transpiled_circuits():

    circuit_files = sorted(
        TRANSPILED_DIR.glob("*.qpy")
    )

    if not circuit_files:
        raise FileNotFoundError(
            f"No QPY files found in {TRANSPILED_DIR}"
        )

    circuits = {}

    for file_path in circuit_files:

        with open(file_path, "rb") as file:
            loaded_circuits = qpy.load(file)

        if len(loaded_circuits) != 1:
            raise ValueError(
                f"Expected one circuit in {file_path}"
            )

        circuit = loaded_circuits[0]

        circuit_id, backend_name = (
            file_path.stem.rsplit("__", 1)
        )

        circuits[(circuit_id, backend_name)] = circuit

    return circuits


# ==========================================
# 5. RUN MODEL A
# ==========================================

def main():

    print("========== MODEL A STARTED ==========")

    calibration = load_gate_calibration()
    circuits = load_transpiled_circuits()

    print("Calibration records:", len(calibration))
    print("Transpiled circuits:", len(circuits))

    results = []

    for (circuit_id, backend_name), circuit in circuits.items():

        score = calculate_success_probability(
            circuit,
            backend_name,
            calibration
        )

        row = {
            "circuit_id": circuit_id,
            "backend_name": backend_name,
            "gate_count": score["gate_count"],
            "log_success_probability":
                score["log_success_probability"],
            "success_probability":
                score["success_probability"]
        }

        results.append(row)

        print(
            f"{circuit_id:15s} | "
            f"{backend_name:12s} | "
            f"Score: {score['success_probability']:.8f}"
        )

    # ======================================
    # 6. SAVE SCORES AND RANK BACKENDS
    # ======================================

    df = pd.DataFrame(results)

    df["rank"] = (
        df.groupby("circuit_id")["success_probability"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    df = df.sort_values(
        ["circuit_id", "rank"]
    )

    df.to_csv(OUTPUT_FILE, index=False)

    print("\n========== MODEL A SUMMARY ==========")
    print("Total predictions:", len(df))
    print("Unique circuits:", df["circuit_id"].nunique())
    print("Unique backends:", df["backend_name"].nunique())

    print("\nRanking preview:")

    for circuit_id, group in df.groupby("circuit_id"):

        print(f"\n{circuit_id}")

        print(
            group[
                [
                    "backend_name",
                    "success_probability",
                    "rank"
                ]
            ].to_string(index=False)
        )

    print("\nCSV saved to:", OUTPUT_FILE)
    print("\nModel A completed successfully!")


if __name__ == "__main__":
    main()
