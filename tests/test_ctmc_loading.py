import os
import sys
import pandas as pd
import pytest

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from analytics.ctmc.population_matrix import load_population_matrix

def test_population_matrix_loads():
    matrix_path = "spedia_anomaly_detection/data/ctmc_transition_matrix.csv"
    assert os.path.exists(matrix_path), "CTMC transition matrix artifact is missing!"
    
    mx = load_population_matrix(matrix_path)
    assert isinstance(mx, dict)
    assert len(mx) > 0, "CTMC matrix loaded but is mysteriously empty!"
    
    # Verify shape/characteristics
    for state, transitions in mx.items():
        assert isinstance(state, str)
        assert isinstance(transitions, dict)
        
        # Probabilities should roughly sum to 1.0 depending on precision
        total_prob = sum(transitions.values())
        assert 0.99 <= total_prob <= 1.01, f"Transitions for {state} do not sum to 1.0"
