
import ast
import json
import math
from pathlib import Path

import pandas as pd
from qiskit import qpy
from qiskit.converters import circuit_to_dag


PROJECT_ROOT = Path(__file__).resolve().parents[2]

GATE_FILE = PROJECT_ROOT / "data/calibration/gate_calibration.csv"
TRANSPILED_DIR = PROJECT_ROOT / "data/transpiled"
OUTPUT_DIR = PROJECT_ROOT / "data/processed"

OUTPUT_FILE = OUTPUT_DIR / "model_b_scores.csv"

IGNORED_GATES = {"barrier", "measure", "delay"}


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
                f"Invalid gate error: {key}, error={error}"
            )

        calibration[key] = error

    return calibration


def load_transpiled_circuits():
    circuit_files = sorted(TRANSPILED_DIR.glob("*.qpy"))

    if not circuit_files:
        raise FileNotFoundError(
            f"No QPY files found in {TRANSPILED_DIR}"
        )

    circuits = {}

    for file_path in circuit_files:
        circuit_id, backend_name = file_path.stem.rsplit("__", 1)

        with open(file_path, "rb") as file:
            loaded = qpy.load(file)

        if len(loaded) != 1:
            raise ValueError(
                f"Expected one circuit in {file_path}"
            )

        circuits[(circuit_id, backend_name)] = loaded[0]

    return circuits


def calculate_layer_error(circuit, backend_name, calibration):
    dag = circuit_to_dag(circuit)

    layer_results = []

    for layer_index, layer in enumerate(dag.layers()):
        operation_nodes = layer["graph"].op_nodes()

        gate_errors = []

        for node in operation_nodes:
            if node.name in IGNORED_GATES:
                continue

            physical_qubits = tuple(
                circuit.find_bit(qubit).index
                for qubit in node.qargs
            )

            key = (
                backend_name,
                node.name,
                physical_qubits
            )

            if key not in calibration:
                raise KeyError(
                    f"Missing calibration: {key}"
                )

            gate_errors.append(calibration[key])

        if not gate_errors:
            continue

        # Probability that at least one gate in this layer fails.
        layer_success = math.prod(
            1.0 - error for error in gate_errors
        )

        layer_error = 1.0 - layer_success

        layer_results.append({
            "layer_index": layer_index,
            "gate_count": len(gate_errors),
            "layer_error": layer_error,
            "layer_success": layer_success
        })

    if not layer_results:
        raise ValueError(
            f"No valid gates found in {circuit.name}"
        )

    num_layers = len(layer_results)

    mean_layer_error = sum(
        item["layer_error"] for item in layer_results
    ) / num_layers

    mean_layer_success = 1.0 - mean_layer_error

    return {
        "num_layers": num_layers,
        "total_gates": sum(
            item["gate_count"] for item in layer_results
        ),
        "mean_layer_error": mean_layer_error,
        "mean_layer_success": mean_layer_success,
        "max_layer_error": max(
            item["layer_error"] for item in layer_results
        ),
        "layer_error_std": pd.Series(
            [item["layer_error"] for item in layer_results]
        ).std(ddof=0)
    }


def main():
    print("========== MODEL B STARTED ==========")

    calibration = load_gate_calibration()
    circuits = load_transpiled_circuits()

    print("Calibration records:", len(calibration))
    print("Transpiled circuits:", len(circuits))

    results = []

    for (circuit_id, backend_name), circuit in circuits.items():

        score = calculate_layer_error(
            circuit,
            backend_name,
            calibration
        )

        results.append({
            "circuit_id": circuit_id,
            "backend_name": backend_name,
            "num_layers": score["num_layers"],
            "total_gates": score["total_gates"],
            "mean_layer_error": score["mean_layer_error"],
            "mean_layer_success": score["mean_layer_success"],
            "max_layer_error": score["max_layer_error"],
            "layer_error_std": score["layer_error_std"]
        })

        print(
            f"{circuit_id:15s} | "
            f"{backend_name:12s} | "
            f"Mean layer success: "
            f"{score['mean_layer_success']:.8f}"
        )

    df = pd.DataFrame(results)

    df["rank"] = (
        df.groupby("circuit_id")["mean_layer_success"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    df = df.sort_values(["circuit_id", "rank"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print("\n========== MODEL B SUMMARY ==========")
    print("Total predictions:", len(df))
    print("Unique circuits:", df["circuit_id"].nunique())
    print("Unique backends:", df["backend_name"].nunique())

    for circuit_id, group in df.groupby("circuit_id"):
        print(f"\n{circuit_id}")
        print(
            group[
                [
                    "backend_name",
                    "mean_layer_success",
                    "mean_layer_error",
                    "rank"
                ]
            ].to_string(index=False)
        )

    print("\nCSV saved to:", OUTPUT_FILE)
    print("Model B completed successfully!")


if __name__ == "__main__":
    main()
