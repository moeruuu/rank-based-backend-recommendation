"""Reproducible shot-based noise simulations using Qiskit Aer and the four fake devices.

Requires qiskit, qiskit-aer, qiskit-ibm-runtime at execution time.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

BACKENDS = ("fake_manila", "fake_lima", "fake_athens", "fake_belem")


def load_backends():
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2, FakeLimaV2, FakeAthensV2, FakeBelemV2
    instances = (FakeManilaV2(), FakeLimaV2(), FakeAthensV2(), FakeBelemV2())
    return {b.name: b for b in instances}


def load_circuits(directory: str | Path):
    from qiskit import qpy
    directory = Path(directory)
    circuits = {}
    for path in sorted(directory.glob("*.qpy")):
        with path.open("rb") as stream:
            loaded = qpy.load(stream)
        if len(loaded) != 1:
            raise ValueError(f"Expected exactly one circuit in {path}")
        circuits[path.stem] = loaded[0]
    if not circuits:
        raise ValueError(f"No .qpy circuit files in {directory}")
    return circuits


def ideal_probabilities(circuit):
    """Reference measurement distribution of ideal (noiseless) quantum circuit."""
    from qiskit.quantum_info import Statevector
    clean = circuit.remove_final_measurements(inplace=False)
    state = Statevector.from_instruction(clean)
    return np.asarray(state.probabilities(), dtype=float)


def observed_probabilities(counts: dict, num_qubits: int) -> np.ndarray:
    """Qiskit bitstrings are little-endian with q0 on the right."""
    probabilities = np.zeros(2 ** num_qubits, dtype=float)
    shots = sum(counts.values())
    if shots <= 0:
        raise ValueError("The counts dictionary is empty")
    for key, count in counts.items():
        binary = key.replace(" ", "")
        index = int(binary, 2)
        if index >= len(probabilities):
            raise ValueError(f"Unexpected classical outcome {key!r}")
        probabilities[index] += count / shots
    return probabilities


def distribution_fidelity(p: np.ndarray, q: np.ndarray) -> float:
    """Classical squared Bhattacharyya coefficient, in [0, 1]. Not quantum state fidelity."""
    if p.shape != q.shape:
        raise ValueError("Mismatched distributions")
    return float(np.clip(np.sum(np.sqrt(p * q)) ** 2, 0, 1))


def total_variation_distance(p: np.ndarray, q: np.ndarray) -> float:
    return float(0.5 * np.abs(p - q).sum())


def run_simulation(circuits_dir="data/circuits", output_dir="data/results", shots=4096,
                   seeds=(42, 100, 202), optimization_level=1, backend_names=None):
    """Measure every logical qubit after transpilation to each fake backend.

    Ranking labels come from mean observed distribution fidelity per circuit/backend.
    """
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    if shots < 1 or not seeds or optimization_level not in (0, 1, 2, 3):
        raise ValueError("Require shots>=1, nonempty seeds, and optimization_level 0..3")
    if len(set(seeds)) != len(seeds):
        raise ValueError("Seeds must be unique")
    backends = load_backends()
    names = tuple(backend_names) if backend_names is not None else BACKENDS
    if not names or any(name not in backends for name in names):
        raise ValueError(f"Unknown backend name: {names}")
    circuits = load_circuits(circuits_dir)
    rows = []
    for circuit_id, circuit in circuits.items():
        if circuit.num_clbits:
            raise ValueError(f"Circuit {circuit_id} must have no pre-existing classical bits")
        ideal = ideal_probabilities(circuit)
        for name in names:
            backend = backends[name]
            if circuit.num_qubits > backend.num_qubits:
                continue
            # Simulator.from_backend reads calibration-based gate, readout and relaxation noise.
            simulator = AerSimulator.from_backend(backend)
            measured = circuit.copy()
            measured.measure_all()
            compiled = transpile(measured, backend=backend, optimization_level=optimization_level,
                                 seed_transpiler=42)
            for seed in seeds:
                counts = simulator.run(compiled, shots=shots, seed_simulator=int(seed)).result().get_counts()
                observed = observed_probabilities(counts, circuit.num_qubits)
                rows.append({
                    "circuit_id": circuit_id,
                    "circuit_type": circuit_id.split("_")[0],
                    "num_qubits": circuit.num_qubits,
                    "backend_name": name,
                    "seed": int(seed),
                    "shots": int(shots),
                    "optimization_level": int(optimization_level),
                    "distribution_fidelity": distribution_fidelity(ideal, observed),
                    "tvd": total_variation_distance(ideal, observed),
                    "counts_json": json.dumps(counts, sort_keys=True),
                })
    if not rows:
        raise ValueError("No compatible circuit/backend pairs")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(output / "noise_simulation_runs.csv", index=False)
    summary = df.groupby(["circuit_id", "backend_name"], as_index=False).agg(
        num_qubits=("num_qubits", "first"),
        mean_fidelity=("distribution_fidelity", "mean"),
        std_fidelity=("distribution_fidelity", "std"),
        mean_tvd=("tvd", "mean"),
        runs=("seed", "size"),
    )
    summary["std_fidelity"] = summary["std_fidelity"].fillna(0)
    summary.to_csv(output / "noise_simulation_summary.csv", index=False)
    return df, summary
