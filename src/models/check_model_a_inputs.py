
import json
from pathlib import Path

import pandas as pd
from qiskit import qpy

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GATE_FILE = PROJECT_ROOT / "data/calibration/gate_calibration.csv"
TRANSPILED_DIR = PROJECT_ROOT / "data/transpiled"

gate_df = pd.read_csv(GATE_FILE)

# Tạo tập hợp các gate calibration đã có
calibration_keys = set()

for _, row in gate_df.iterrows():
    qubits = tuple(json.loads(row["qubits"]))

    key = (
        row["backend_name"],
        row["gate_name"],
        qubits
    )

    calibration_keys.add(key)

print("Calibration records:", len(calibration_keys))

ignored_gates = {"barrier", "measure", "delay"}

total_gates = 0
missing_gates = []

# Kiểm tra từng circuit trên từng backend
for file_path in sorted(TRANSPILED_DIR.glob("*.qpy")):

    with open(file_path, "rb") as file:
        circuits = qpy.load(file)

    circuit = circuits[0]

    circuit_id, backend_name = file_path.stem.rsplit("__", 1)

    for instruction in circuit.data:

        operation = instruction.operation
        gate_name = operation.name

        if gate_name in ignored_gates:
            continue

        qubits = tuple(
            circuit.find_bit(q).index
            for q in instruction.qubits
        )

        key = (backend_name, gate_name, qubits)

        total_gates += 1

        if key not in calibration_keys:
            missing_gates.append(
                (circuit_id, backend_name, gate_name, qubits)
            )

print("\n========== CHECK SUMMARY ==========")
print("Total gates checked:", total_gates)
print("Missing calibration:", len(missing_gates))

if missing_gates:
    print("\nMissing calibration examples:")

    for item in missing_gates[:20]:
        print(item)
else:
    print("All gates have matching calibration data!")
