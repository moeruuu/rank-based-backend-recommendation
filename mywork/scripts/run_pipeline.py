"""CLI: python -m scripts.run_pipeline [--shots 4096] [--seeds 42 100 202]"""
import argparse
from src.simulation.noise import run_simulation
from src.ranking.ground_truth import save_ground_truth
from src.ranking.baseline import save_baseline
from src.ranking.evaluate import save_evaluation


def main():
    parser = argparse.ArgumentParser(description="Noise simulation -> ground truth -> ranking metrics")
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 100, 202])
    parser.add_argument("--optimization-level", type=int, default=1, choices=[0, 1, 2, 3])
    args = parser.parse_args()
    _, summary = run_simulation(shots=args.shots, seeds=args.seeds, optimization_level=args.optimization_level)
    gt = save_ground_truth()
    predictions = save_baseline()
    detail, mean = save_evaluation()
    print(f"Simulation: {len(summary)} circuit/backend pairs; ground truth: {len(gt)} labels")
    print(f"Baseline: {len(predictions)} predictions; evaluated circuits: {len(detail)}")
    print(mean.to_string(index=False))
    print("Results saved under data/results/")


if __name__ == "__main__":
    main()
