
from qiskit import QuantumCircuit


def create_ghz(n):
    """
    Create an n-qubit GHZ circuit.

    Args:
        n: Number of qubits.

    Returns:
        QuantumCircuit
    """

    if n < 2:
        raise ValueError("GHZ circuit requires at least 2 qubits.")

    qc = QuantumCircuit(n)

    # Apply Hadamard gate to the first qubit
    qc.h(0)

    # Entangle all qubits using CNOT gates
    for i in range(n - 1):
        qc.cx(i, i + 1)

    return qc


if __name__ == "__main__":

    for n in [3, 5]:

        circuit = create_ghz(n)

        print(f"\nGHZ {n} QUBITS")
        print(circuit.draw())

        print("Number of qubits:", circuit.num_qubits)
        print("Circuit depth:", circuit.depth())
        print("Gate counts:", circuit.count_ops())
