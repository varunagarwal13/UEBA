"""
Confidence-weighted fusion: combine N EngineOutputs into one risk score
via inverse-variance weighting, with an optional weight floor so a
single high-confidence engine can never get crushed to near-zero
influence just because the others happen to be noisy right now.
"""

from typing import List, Tuple

from src.common.schema import EngineOutput


def inverse_variance_fuse(
    outputs: List[EngineOutput],
    min_weight: float = 0.0,
) -> Tuple[float, float, List[float]]:
    """
    Returns (fused_score, fused_variance, weights_used).

    min_weight: floor each engine's weight at this value (0-1) before
    renormalizing, so a screaming high-score engine with temporarily
    high variance (e.g. a cold-start user for CTMC) still gets some
    say in the final number. 0.0 disables the floor (pure inverse-
    variance weighting).
    """
    if not outputs:
        raise ValueError("Need at least one EngineOutput to fuse")

    precisions = [1.0 / max(o.variance, 1e-6) for o in outputs]
    total_precision = sum(precisions)
    weights = [p / total_precision for p in precisions]

    if min_weight > 0:
        weights = [max(w, min_weight) for w in weights]
        weight_sum = sum(weights)
        weights = [w / weight_sum for w in weights]

    fused_score = sum(w * o.score for w, o in zip(weights, outputs))
    fused_variance = 1.0 / total_precision

    return fused_score, fused_variance, weights
