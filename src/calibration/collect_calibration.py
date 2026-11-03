
import json
from pathlib import Path

import pandas as pd

from qiskit_ibm_runtime.fake_provider import (
    FakeManilaV2,
    FakeLimaV2,
    FakeAthensV2,
    FakeBelemV2,
)

#1. Khởi tạo 4 fake backend
backends = [
    FakeManilaV2(),
    FakeLimaV2(),
    FakeAthensV2(),
    FakeBelemV2(),
]

qubit_rows = []
gate_rows = []
backend_rows = []

#2. Thu thập calibration của từng backend
for backend in backends:

    print(f"Collecting: {backend.name}")

    target = backend.target
    coupling_map = backend.coupling_map

    edges = (
        list(coupling_map.get_edges())
        if coupling_map is not None
        else []
    )

    #Thông tin tổng quan backend
    backend_rows.append({
        "backend_name": backend.name,
        "num_qubits": backend.num_qubits,
        "coupling_map": json.dumps(edges),
        "basis_gates": json.dumps(
            sorted(target.operation_names)
        )
    })

    #3. Thu thập thông tin từng qubit
    for q in range(backend.num_qubits):

        properties = backend.qubit_properties(q)

        t1 = properties.t1 if properties else None
        t2 = properties.t2 if properties else None

        measure_props = target["measure"].get((q,))

        readout_error = (
            measure_props.error
            if measure_props is not None
            else None
        )

        qubit_rows.append({
            "backend_name": backend.name,
            "qubit": q,
            "t1_seconds": t1,
            "t2_seconds": t2,
            "readout_error": readout_error
        })

    #4. Thu thập thông tin các cổng lượng tử
    for gate_name in target.operation_names:

        if gate_name in [
            "measure",
            "reset",
            "delay",
            "switch_case",
            "for_loop",
            "if_else"
        ]:
            continue

        try:
            gate_map = target[gate_name]

            for qubits, gate_props in gate_map.items():

                gate_rows.append({
                    "backend_name": backend.name,
                    "gate_name": gate_name,
                    "qubits": json.dumps(list(qubits)),
                    "gate_error": (
                        gate_props.error
                        if gate_props is not None
                        else None
                    ),
                    "gate_duration_seconds": (
                        gate_props.duration
                        if gate_props is not None
                        else None
                    )
                })

        except (KeyError, TypeError, AttributeError):
            continue


#5. Chuyển dữ liệu thành DataFrame
qubit_df = pd.DataFrame(qubit_rows)
gate_df = pd.DataFrame(gate_rows)
backend_df = pd.DataFrame(backend_rows)

#6. Tạo thư mục lưu dữ liệu
output_dir = Path("data/calibration")
output_dir.mkdir(parents=True, exist_ok=True)

#7. Xuất CSV
qubit_df.to_csv(
    output_dir / "qubit_calibration.csv",
    index=False
)

gate_df.to_csv(
    output_dir / "gate_calibration.csv",
    index=False
)

backend_df.to_csv(
    output_dir / "backend_summary.csv",
    index=False
)

print("\nCalibration collection completed!")
print("Qubit records:", len(qubit_df))
print("Gate records:", len(gate_df))
print("Backend records:", len(backend_df))
