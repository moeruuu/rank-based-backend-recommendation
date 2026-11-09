
from pathlib import Path
from qiskit import qpy
from qiskit.converters import circuit_to_dag
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRANSPILED_DIR = PROJECT_ROOT / "data/transpiled"
OUTPUT_FILE = PROJECT_ROOT / "data/processed/circuit_layer_features.csv"


def analyze_circuit(circuit):
    dag = circuit_to_dag(circuit)

    layers = []

    for layer_index, layer in enumerate(dag.layers()):
        operation_nodes = layer["graph"].op_nodes()

        gates = []

        for node in operation_nodes:
            if node.name in {"barrier", "measure", "delay"}:
                continue

            gates.append({
                "name": node.name,
                "qubits": [
                    circuit.find_bit(qubit).index
                    for qubit in node.qargs
                ]
            })

        if gates:
            layers.append({
                "layer_index": layer_index,
                "gate_count": len(gates),
                "gates": gates
            })

    return layers


def main():
    print("========== CIRCUIT LAYER ANALYSIS ==========")

    circuit_files = sorted(TRANSPILED_DIR.glob("*.qpy"))

    if not circuit_files:
        raise FileNotFoundError("No transpiled QPY files found.")

    results = []

    for file_path in circuit_files:
        circuit_id, backend_name = file_path.stem.rsplit("__", 1)

        with open(file_path, "rb") as file:
            circuit = qpy.load(file)[0]

        layers = analyze_circuit(circuit)

        total_gates = sum(
            layer["gate_count"] for layer in layers
        )

        results.append({
            "circuit_id": circuit_id,
            "backend_name": backend_name,
            "depth": circuit.depth(),
            "num_layers": len(layers),
            "total_gates": total_gates,
            "max_gates_per_layer": max(
                (layer["gate_count"] for layer in layers),
                default=0
            ),
            "layer_details": str(layers)
        })

        print(
            f"{circuit_id:15s} | "
            f"{backend_name:12s} | "
            f"Depth: {circuit.depth():3d} | "
            f"Layers: {len(layers):3d} | "
            f"Gates: {total_gates:3d}"
        )

    df = pd.DataFrame(results)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print("\n========== SUMMARY ==========")
    print("Total circuits:", len(df))
    print("Unique circuit IDs:", df["circuit_id"].nunique())
    print("Unique backends:", df["backend_name"].nunique())
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
