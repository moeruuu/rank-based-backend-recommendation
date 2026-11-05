
import json
from pathlib import Path

import pandas as pd
from qiskit import qpy, transpile

from qiskit_ibm_runtime.fake_provider import (
    FakeManilaV2,
    FakeLimaV2,
    FakeAthensV2,
    FakeBelemV2,
)


# ============================================================
# 1. Project paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = PROJECT_ROOT / "data" / "circuits"
OUTPUT_DIR = PROJECT_ROOT / "data" / "transpiled"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. Initialize the same fake backends used in M1
# ============================================================

BACKENDS = [
    FakeManilaV2(),
    FakeLimaV2(),
    FakeAthensV2(),
    FakeBelemV2(),
]


# ============================================================
# 3. Extract features from a transpiled circuit
# ============================================================

def extract_transpiled_features(circuit):
    ignored_gates = {"barrier", "measure", "delay"}

    gate_composition = {}
    single_qubit_gates = 0
    two_qubit_gates = 0

    for instruction in circuit.data:
        operation = instruction.operation
        gate_name = operation.name

        if gate_name in ignored_gates:
            continue

        gate_composition[gate_name] = (
            gate_composition.get(gate_name, 0) + 1
        )

        if operation.num_qubits == 1:
            single_qubit_gates += 1

        elif operation.num_qubits == 2:
            two_qubit_gates += 1

    return {
        "transpiled_num_qubits": circuit.num_qubits,
        "depth": circuit.depth(),
        "num_gates": sum(gate_composition.values()),
        "single_qubit_gates": single_qubit_gates,
        "two_qubit_gates": two_qubit_gates,
        "gate_composition": json.dumps(gate_composition),
        "cx_count": gate_composition.get("cx", 0),
        "sx_count": gate_composition.get("sx", 0),
        "rz_count": gate_composition.get("rz", 0),
        "x_count": gate_composition.get("x", 0),
    }


# ============================================================
# 4. Load original circuits from QPY files
# ============================================================

def load_circuits():
    circuit_files = sorted(INPUT_DIR.glob("*.qpy"))

    if not circuit_files:
        raise FileNotFoundError(
            f"No QPY circuits found in {INPUT_DIR}"
        )

    circuits = {}

    for file_path in circuit_files:
        with open(file_path, "rb") as file:
            loaded_circuits = qpy.load(file)

        if len(loaded_circuits) != 1:
            raise ValueError(
                f"Expected one circuit in {file_path.name}, "
                f"found {len(loaded_circuits)}"
            )

        circuit_id = file_path.stem
        circuits[circuit_id] = loaded_circuits[0]

        print(
            f"Loaded: {circuit_id} "
            f"({loaded_circuits[0].num_qubits} qubits)"
        )

    return circuits


# ============================================================
# 5. Transpile every circuit for every backend
# ============================================================

def main():
    circuits = load_circuits()

    results = []

    total_pairs = len(circuits) * len(BACKENDS)
    successful_pairs = 0
    failed_pairs = 0

    print("\n========== TRANSPILATION STARTED ==========")
    print("Circuits:", len(circuits))
    print("Backends:", len(BACKENDS))
    print("Expected pairs:", total_pairs)

    for circuit_id, original_circuit in circuits.items():

        for backend in BACKENDS:

            backend_name = backend.name

            print(
                f"\nTranspiling {circuit_id} "
                f"for {backend_name}..."
            )

            row = {
                "circuit_id": circuit_id,
                "backend_name": backend_name,
                "original_num_qubits": original_circuit.num_qubits,
                "status": "failed",
                "error_message": None,
            }

            try:
                compiled_circuit = transpile(
                    original_circuit,
                    backend=backend,
                    optimization_level=1,
                    seed_transpiler=42,
                )

                # Save compiled circuit
                output_file = (
                    OUTPUT_DIR
                    / f"{circuit_id}__{backend_name}.qpy"
                )

                with open(output_file, "wb") as file:
                    qpy.dump(compiled_circuit, file)

                # Extract features
                features = extract_transpiled_features(
                    compiled_circuit
                )

                row.update(features)
                row["status"] = "success"
                row["output_file"] = str(
                    output_file.relative_to(PROJECT_ROOT)
                )

                successful_pairs += 1

                print(
                    f"Success | Depth: {features['depth']} "
                    f"| Gates: {features['num_gates']}"
                )

            except Exception as error:
                row["error_message"] = (
                    f"{type(error).__name__}: {error}"
                )

                failed_pairs += 1

                print("Failed:", row["error_message"])

            results.append(row)

    # ========================================================
    # 6. Export results to CSV
    # ========================================================

    df = pd.DataFrame(results)

    output_csv = (
        PROCESSED_DIR / "transpiled_features.csv"
    )

    df.to_csv(output_csv, index=False)

    # ========================================================
    # 7. Display summary
    # ========================================================

    print("\n========== TRANSPILATION SUMMARY ==========")

    print("Total pairs:", total_pairs)
    print("Successful:", successful_pairs)
    print("Failed:", failed_pairs)

    print("\nResults by backend:")

    print(
        df.groupby(["backend_name", "status"])
        .size()
        .unstack(fill_value=0)
    )

    print("\nDataset preview:")
    print(
        df[
            [
                "circuit_id",
                "backend_name",
                "depth",
                "num_gates",
                "single_qubit_gates",
                "two_qubit_gates",
                "status",
            ]
        ].to_string(index=False)
    )

    print("\nCSV saved to:", output_csv)
    print("\nTranspilation process completed!")


if __name__ == "__main__":
    main()
