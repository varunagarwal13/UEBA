import json
from datetime import datetime
from typing import Dict, Any, List
from analytics.profiling.behavioral_profile import BehavioralProfileState, ProfileStatistics

class ProfileBuilder:
    """
    Handles robust incremental statistical updates for Behavioral profiles.
    Rejects immediate baseline corruption during massive anomalies via configurable boundaries.
    """
    
    def __init__(self, anomaly_update_threshold_z: float = 4.0):
        # We do not immediately pollute the baseline if a session's variance exceeds 4.0 Z
        self.anomaly_update_threshold_z = anomaly_update_threshold_z

    def deserialize(self, user_id: str, session_count: int, stats_json: str, state_json: str, action_json: str, confidence: float) -> BehavioralProfileState:
        profile = BehavioralProfileState(user_id=user_id, session_count=session_count, confidence=confidence)
        try:
            raw_stats = json.loads(stats_json) if stats_json else {}
            for k, v in raw_stats.items():
                profile.statistics[k] = ProfileStatistics(**v)
        except:
            pass
            
        try:
            profile.state_distribution = json.loads(state_json) if state_json else {}
        except:
            pass 

        try:
            profile.action_distribution = json.loads(action_json) if action_json else {}
        except:
            pass
            
        return profile

    def serialize_stats(self, profile: BehavioralProfileState) -> str:
        d = {k: v.__dict__ for k, v in profile.statistics.items()}
        return json.dumps(d)

    def update_profile(self, profile: BehavioralProfileState, features: Dict[str, float], is_anomalous: bool = False, max_z_observed: float = 0.0):
        """
        Incrementally updates mean/variance using Welford's online algorithm.
        Do NOT rigidly fold highly anomalous activity into the baseline.
        """
        # Rule of Update Policy: if max deviation > Threshold, dampen update rate to prevent baseline poisoning
        learning_rate = 1.0
        if max_z_observed > self.anomaly_update_threshold_z:
            learning_rate = 0.1 # 90% resistance to outlier poisoning

        for feature_name, value in features.items():
            if feature_name not in profile.statistics:
                profile.statistics[feature_name] = ProfileStatistics(count=0, min_val=value, max_val=value)
            
            s = profile.statistics[feature_name]
            
            # Welford's incremental mean/variance
            s.count += 1
            s.min_val = min(s.min_val, value)
            s.max_val = max(s.max_val, value)
            
            # Apply dampening for outliers
            delta = value - s.mean
            s.mean += (delta / s.count) * learning_rate
            delta2 = value - s.mean
            s.variance += (delta * delta2) * learning_rate
            
        profile.session_count += 1
        
        # update confidence
        if profile.session_count < 5:
            profile.confidence = 0.2
        elif profile.session_count < 15:
            profile.confidence = 0.6
        else:
            profile.confidence = min(1.0, profile.confidence + 0.05)
