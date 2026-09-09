import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pytest
from analytics.profiling.behavioral_profile import BehavioralProfileState
from analytics.profiling.profile_builder import ProfileBuilder
from analytics.profiling.profile_comparator import ProfileComparator

def test_profile_cold_start():
    comp = ProfileComparator()
    prof = BehavioralProfileState("u1", session_count=2)
    score, res = comp.compare(prof, {"file_access": 5.0})
    
    assert score == 0.0
    assert res["behavioral_deviation"]["available"] == False
    assert res["behavioral_deviation"]["profile_state"] == "NEW"

def test_profile_learning():
    comp = ProfileComparator()
    # 6 sessions = LEARNING
    prof = BehavioralProfileState("u1", session_count=6)
    builder = ProfileBuilder()
    
    # establish baseline
    for _ in range(6):
        builder.update_profile(prof, {"file_access": 10.0})
        
    score, res = comp.compare(prof, {"file_access": 50.0}) # highly deviant
    
    assert res["behavioral_deviation"]["available"] == True
    assert res["behavioral_deviation"]["profile_state"] == "LEARNING"
    # learning state dampens the raw score explicitly
    assert score > 0.0 and score <= 50.0 

def test_profile_update_policy():
    prof = BehavioralProfileState("u1", session_count=20)
    builder = ProfileBuilder(anomaly_update_threshold_z= 4.0)
    
    # Establish extremely solid baseline for 20 sessions (average 10)
    for _ in range(20):
        builder.update_profile(prof, {"login_count": 10.0}, max_z_observed=0.0)
        
    old_mean = prof.statistics["login_count"].mean
    
    # Observe extreme spike (anomaly). This shouldn't shift the mean by much due to dampening.
    builder.update_profile(prof, {"login_count": 1000.0}, max_z_observed=10.0) # Z score of 10.0 is > 4.0
    
    new_mean = prof.statistics["login_count"].mean
    
    # without dampening, new_mean = (200 + 1000) / 21 = 57. 
    # with 0.1 dampening, delta is (1000 - 10) = 990. 990 / 21 * 0.1 = 4.7.  New mean ~ 14.7.
    assert new_mean < 25.0, "Update policy failed to dampen baseline poisoning from extreme anomaly."
    assert new_mean > old_mean
