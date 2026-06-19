"""
Sanity test for fusion math, using the exact worked example we derived
by hand: rules=70 (var=4), ecod=55 (var=25), hdbscan=40 (var=16),
ctmc=85 (var=64). Expected fused score ~= 63.9.
"""

from src.common.schema import EngineOutput
from src.fusion.fuse import inverse_variance_fuse


def test_inverse_variance_matches_hand_calculation():
    outputs = [
        EngineOutput(score=70, variance=4),  # rules
        EngineOutput(score=55, variance=25),  # ecod
        EngineOutput(score=40, variance=16),  # hdbscan
        EngineOutput(score=85, variance=64),  # ctmc
    ]

    fused_score, fused_variance, weights = inverse_variance_fuse(outputs)

    assert abs(fused_score - 63.9) < 0.2
    assert abs(weights[0] - 0.679) < 0.01  # rules carries most of the weight
    assert abs(weights[3] - 0.042) < 0.01  # cold-start ctmc gets crushed


def test_min_weight_floor_protects_low_confidence_engines():
    outputs = [
        EngineOutput(score=70, variance=4),
        EngineOutput(score=85, variance=64),
    ]

    _, _, weights_no_floor = inverse_variance_fuse(outputs)
    _, _, weights_floored = inverse_variance_fuse(outputs, min_weight=0.1)

    assert weights_floored[1] > weights_no_floor[1]
