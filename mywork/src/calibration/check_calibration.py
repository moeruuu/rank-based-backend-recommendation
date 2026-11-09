
import pandas as pd

qubits = pd.read_csv(
    "data/calibration/qubit_calibration.csv"
)

gates = pd.read_csv(
    "data/calibration/gate_calibration.csv"
)

backends = pd.read_csv(
    "data/calibration/backend_summary.csv"
)

print("Number of backends:", len(backends))
print("Number of qubit records:", len(qubits))
print("Number of gate records:", len(gates))

print("\nMissing values:")
print(qubits.isnull().sum())

print("\nBackend list:")
print(backends["backend_name"].tolist())

print("\nAverage T1:")
print(qubits.groupby("backend_name")["t1_seconds"].mean())

print("\nAverage T2:")
print(qubits.groupby("backend_name")["t2_seconds"].mean())

print("\nAverage readout error:")
print(qubits.groupby("backend_name")["readout_error"].mean())

print("\nAverage gate error:")
print(gates.groupby("backend_name")["gate_error"].mean())
