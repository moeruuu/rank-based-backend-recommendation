
import json
from pathlib import Path

import pandas as pd

from src.circuits.ghz import create_ghz
from src.circuits.qft import create_qft
from src.circuits.random_circuit import create_random_circuit


def extract_features(circuit, circuit_id, circuit_type, seed=None):

    # Count operations
    operations = circuit.count_ops()

    # Exclude non-computational operations
    ignored_gates = {"barrier", "measure", "delay"}

    single_qubit_gates = 0
    two_qubit_gates = 0

    # Count gates according to number of qubits
    for instruction in circuit.data:

        operation = instruction.operation
        gate_name = operation.name

        if gate_name in ignored_gates:
            continue

        if operation.num_qubits == 1:
            single_qubit_gates += 1

        elif operation.num_qubits == 2:
            two_qubit_gates += 1

    # Create feature dictionary
    features = {

        "circuit_id": circuit_id,

        "circuit_type": circuit_type,

        "num_qubits": circuit.num_qubits,

        "depth": circuit.depth(),

        "num_gates": sum(
            count
            for gate, count in operations.items()
            if gate not in ignored_gates
        ),

        "single_qubit_gates": single_qubit_gates,

        "two_qubit_gates": two_qubit_gates,

        "h_count": operations.get("h", 0),

        "cx_count": operations.get("cx", 0),

        "cp_count": operations.get("cp", 0),

        "swap_count": operations.get("swap", 0),

        "gate_composition": json.dumps(
            {
                gate: count
                for gate, count in operations.items()
                if gate not in ignored_gates
            }
        ),

        "random_seed": seed

    }

    return features


def main():

    all_features = []

    # 1. Generate GHZ circuits
    for n in [3, 5]:

        circuit = create_ghz(n)

        features = extract_features(
            circuit,
            f"GHZ_{n}",
            "GHZ"
        )

        all_features.append(features)

    # 2. Generate QFT circuits
    for n in [3, 5]:

        circuit = create_qft(n)

        features = extract_features(
            circuit,
            f"QFT_{n}",
            "QFT"
        )

        all_features.append(features)

    # 3. Generate Random circuits
    for n in [3, 5]:

        for seed in [42, 100, 202]:

            circuit = create_random_circuit(
                n=n,
                depth=5,
                seed=seed
            )

            features = extract_features(
                circuit,
                f"RANDOM_{n}_{seed}",
                "Random",
                seed
            )

            all_features.append(features)

    # 4. Convert to DataFrame
    df = pd.DataFrame(all_features)

    # 5. Create output directory
    output_dir = Path("data/circuits")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 6. Export CSV
    output_path = output_dir / "circuit_features.csv"

    df.to_csv(output_path, index=False)

    # 7. Display results
    print("\n===== CIRCUIT FEATURES DATASET =====")

    print(df.to_string(index=False))

    print("\nTotal circuits:", len(df))

    print("\nCircuit types:")
    print(df["circuit_type"].value_counts())

    print("\nDataset saved to:", output_path)

    print("\nCircuit features exported successfully!")


if __name__ == "__main__":
    main()
