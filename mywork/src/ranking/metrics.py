"""Ranking metrics for ordered backend recommendations, without Qiskit dependencies."""
from __future__ import annotations
import math
from typing import Mapping, Sequence


def _check(actual: Sequence[str], predicted: Sequence[str]) -> None:
    if not actual or len(set(actual)) != len(actual):
        raise ValueError("Ground-truth ranking must contain unique backends and be nonempty")
    if len(set(predicted)) != len(predicted) or set(actual) != set(predicted):
        raise ValueError("Predicted ranking must contain exactly the same unique backend names")


def spearman_rho(actual: Sequence[str], predicted: Sequence[str]) -> float:
    """Spearman rank correlation. Returns 1 for a one-backend ranking."""
    _check(actual, predicted)
    n = len(actual)
    if n == 1:
        return 1.0
    positions = {name: i for i, name in enumerate(predicted)}
    sum_sq = sum((i - positions[name]) ** 2 for i, name in enumerate(actual))
    return 1.0 - 6.0 * sum_sq / (n * (n * n - 1))


def kendall_tau(actual: Sequence[str], predicted: Sequence[str]) -> float:
    """Kendall tau-a for complete, strictly ordered lists (deterministic tie-break)."""
    _check(actual, predicted)
    if len(actual) == 1:
        return 1.0
    rank = {name: i for i, name in enumerate(predicted)}
    concordant, discordant = 0, 0
    for i in range(len(actual)):
        for j in range(i + 1, len(actual)):
            if rank[actual[i]] < rank[actual[j]]:
                concordant += 1
            else:
                discordant += 1
    return (concordant - discordant) / (concordant + discordant)


def top_k_hit(actual: Sequence[str], predicted: Sequence[str], k: int = 1) -> float:
    """1 if the actual best backend is within the model's top k, else 0."""
    _check(actual, predicted)
    if not 1 <= k <= len(actual):
        raise ValueError("k must be between 1 and the number of candidates")
    return float(actual[0] in predicted[:k])


def precision_at_k(actual: Sequence[str], predicted: Sequence[str], k: int) -> float:
    """Fraction of predicted top-k that belong to the actual top-k."""
    _check(actual, predicted)
    if not 1 <= k <= len(actual):
        raise ValueError("k must be between 1 and the number of candidates")
    return len(set(actual[:k]) & set(predicted[:k])) / k


def mrr(actual: Sequence[str], predicted: Sequence[str]) -> float:
    """Reciprocal rank of actual best candidate in the predicted list."""
    _check(actual, predicted)
    return 1.0 / (predicted.index(actual[0]) + 1)


def ndcg_at_k(predicted: Sequence[str], relevance: Mapping[str, float], k: int) -> float:
    """Graded normalized discounted cumulative gain (nonnegative relevance)."""
    if len(set(predicted)) != len(predicted) or set(predicted) != set(relevance):
        raise ValueError("Predicted backends must exactly match the relevance mapping")
    if not 1 <= k <= len(predicted):
        raise ValueError("Invalid k")
    if any(not math.isfinite(float(v)) or v < 0 for v in relevance.values()):
        raise ValueError("Relevance must be finite and nonnegative")
    def dcg(items):
        return sum((2.0 ** float(relevance[x]) - 1.0) / math.log2(i + 2) for i, x in enumerate(items))
    ideal = sorted(relevance, key=lambda x: (-relevance[x], x))[:k]
    denom = dcg(ideal)
    return dcg(predicted[:k]) / denom if denom > 0 else 1.0


def evaluate_ranking(actual: Sequence[str], predicted: Sequence[str], relevance: Mapping[str, float]) -> dict:
    _check(actual, predicted)
    if set(relevance) != set(actual):
        raise ValueError("All candidates need ground-truth relevance")
    return {
        "spearman_rho": spearman_rho(actual, predicted),
        "kendall_tau": kendall_tau(actual, predicted),
        "top1_accuracy": top_k_hit(actual, predicted, 1),
        "top2_hit": top_k_hit(actual, predicted, min(2, len(actual))),
        "precision_at_2": precision_at_k(actual, predicted, min(2, len(actual))),
        "mrr": mrr(actual, predicted),
        "ndcg_at_2": ndcg_at_k(predicted, relevance, min(2, len(actual))),
        "ndcg_at_all": ndcg_at_k(predicted, relevance, len(actual)),
    }
