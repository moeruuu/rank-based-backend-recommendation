
from qiskit.circuit.random import random_circuit


def create_random_circuit(n, depth, seed):
    """
    Generate a random quantum circuit.

    Args:
        n: Number of qubits.
        depth: Requested random circuit depth.
        seed: Random seed for reproducibility.

    Returns:
        QuantumCircuit
    """

    if n < 1:
        raise ValueError("Number of qubits must be positive.")

    if depth < 1:
        raise ValueError("Circuit depth must be positive.")

    qc = random_circuit(
        num_qubits=n,
        depth=depth,
        max_operands=2,
        measure=False,
        seed=seed
    )

    return qc


if __name__ == "__main__":

    circuit = create_random_circuit(
        n=3,
        depth=5,
        seed=42
    )

    print("\n===== RANDOM CIRCUIT =====")
    print(circuit.draw())

    print("Number of qubits:", circuit.num_qubits)
    print("Circuit depth:", circuit.depth())
    print("Gate counts:", circuit.count_ops())
