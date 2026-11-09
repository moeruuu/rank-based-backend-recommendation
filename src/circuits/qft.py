
import numpy as np
from qiskit import QuantumCircuit


def create_qft(n):
    """
    Create an n-qubit Quantum Fourier Transform circuit.

    Args:
        n: Number of qubits.

    Returns:
        QuantumCircuit
    """

    if n < 1:
        raise ValueError("QFT requires at least 1 qubit.")

    qc = QuantumCircuit(n)

    # Hadamard and controlled phase gates
    for j in range(n):

        qc.h(j)

        for k in range(j + 1, n):

            angle = np.pi / (2 ** (k - j))

            qc.cp(angle, k, j)

    # Reverse qubit order using SWAP gates
    for i in range(n // 2):

        qc.swap(i, n - i - 1)

    return qc


if __name__ == "__main__":

    for n in [3, 5]:

        circuit = create_qft(n)

        print(f"\nQFT {n} QUBITS")
        print(circuit.draw())

        print("Number of qubits:", circuit.num_qubits)
        print("Circuit depth:", circuit.depth())
        print("Gate counts:", circuit.count_ops())
