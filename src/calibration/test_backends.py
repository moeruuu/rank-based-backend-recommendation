from qiskit_ibm_runtime.fake_provider import (
    FakeManilaV2,
    FakeLimaV2,
    FakeAthensV2,
    FakeBelemV2
)

backends = [
    FakeManilaV2(),
    FakeLimaV2(),
    FakeAthensV2(),
    FakeBelemV2()
]

for backend in backends:
    print("========================")
    print("Backend:", backend.name)
    print("Number of qubits:", backend.num_qubits)
    print("Basis gates:", backend.operation_names)
    print("Coupling map:", backend.coupling_map)