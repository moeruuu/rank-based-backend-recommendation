import unittest
import numpy as np
import pandas as pd
from src.ranking.metrics import (spearman_rho, kendall_tau, mrr, ndcg_at_k,
                                 top_k_hit, precision_at_k, evaluate_ranking)
from src.ranking.ground_truth import build_ground_truth
from src.ranking.evaluate import evaluate_predictions
from src.simulation.noise import distribution_fidelity, total_variation_distance, observed_probabilities
from src.ranking.baseline import save_baseline


class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.actual = ["a", "b", "c", "d"]
        self.relevance = {"a": 1.0, "b": .8, "c": .5, "d": .1}

    def test_perfect(self):
        scores = evaluate_ranking(self.actual, self.actual, self.relevance)
        for key, val in scores.items():
            self.assertAlmostEqual(val, 1., msg=key)

    def test_reversed(self):
        other = list(reversed(self.actual))
        self.assertAlmostEqual(spearman_rho(self.actual, other), -1.)
        self.assertAlmostEqual(kendall_tau(self.actual, other), -1.)
        self.assertAlmostEqual(mrr(self.actual, other), .25)
        self.assertEqual(top_k_hit(self.actual, other, 1), 0.)
        self.assertEqual(top_k_hit(self.actual, other, 2), 0.)
        self.assertEqual(precision_at_k(self.actual, other, 2), 0.)
        self.assertLess(ndcg_at_k(other, self.relevance, 4), 1)

    def test_invalid_candidates(self):
        with self.assertRaises(ValueError):
            spearman_rho(["a", "b"], ["a", "c"])
        with self.assertRaises(ValueError):
            ndcg_at_k(["a"], {"a": -1}, 1)

    def test_truth_and_evaluation(self):
        source = pd.DataFrame([
            {"circuit_id": "GHZ_3", "backend_name": "b", "mean_fidelity": .9, "mean_tvd": .1, "runs": 3},
            {"circuit_id": "GHZ_3", "backend_name": "a", "mean_fidelity": .9, "mean_tvd": .1, "runs": 3},
        ])
        truth = build_ground_truth(source)
        self.assertEqual(truth.backend_name.tolist(), ["a", "b"])
        pred = pd.DataFrame({"circuit_id": ["GHZ_3", "GHZ_3"],
                             "backend_name": ["b", "a"], "predicted_rank": [1, 2]})
        detail, summary = evaluate_predictions(truth, pred)
        self.assertEqual(detail.iloc[0].top1_accuracy, 0)
        self.assertEqual(summary.iloc[0].num_circuits, 1)

    def test_distribution(self):
        p = np.array([.5, .5, 0, 0])
        self.assertAlmostEqual(distribution_fidelity(p, p), 1)
        self.assertAlmostEqual(total_variation_distance(p, p), 0)
        self.assertAlmostEqual(distribution_fidelity(p, np.array([0, 0, .5, .5])), 0)
        obs = observed_probabilities({"00": 1, "11": 3}, 2)
        np.testing.assert_allclose(obs, [.25, 0, 0, .75])

    def test_baseline_existing_data(self):
        output = save_baseline()
        self.assertEqual(len(output), 40)
        self.assertEqual(output.circuit_id.nunique(), 10)
        self.assertTrue(output.predicted_score.between(0, 1).all())


if __name__ == '__main__':
    unittest.main()
