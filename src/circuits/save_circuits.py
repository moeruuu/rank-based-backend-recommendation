
from pathlib import Path

from qiskit import qpy

from src.circuits.ghz import create_ghz
from src.circuits.qft import create_qft
from src.circuits.random_circuit import create_random_circuit


def main():

    output_dir = Path("data/circuits")
    output_dir.mkdir(parents=True, exist_ok=True)

    circuits = {}

    # 1. GHZ circuits
    for n in [3, 5]:

        circuits[f"GHZ_{n}"] = create_ghz(n)

    # 2. QFT circuits
    for n in [3, 5]:

        circuits[f"QFT_{n}"] = create_qft(n)

    # 3. Random circuits
    for n in [3, 5]:

        for seed in [42, 100, 202]:

            circuits[f"RANDOM_{n}_{seed}"] = (
                create_random_circuit(
                    n=n,
                    depth=5,
                    seed=seed
                )
            )

    # 4. Save each circuit as a QPY file
    for circuit_id, circuit in circuits.items():

        file_path = output_dir / f"{circuit_id}.qpy"

        with open(file_path, "wb") as file:
            qpy.dump(circuit, file)

        print(f"Saved: {file_path}")

    print("\nTotal saved circuits:", len(circuits))
    print("All circuits saved successfully!")


if __name__ == "__main__":
    main()
