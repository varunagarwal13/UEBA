import numpy as np
from typing import Dict, Any, List, Tuple
from analytics.profiling.behavioral_profile import BehavioralProfileState

class ProfileComparator:
    """
    Computes statistical deviation of a new session against a tracked behavioral profile.
    Outputs the final JSON structure requested for V2.1.
    """
    
    def __init__(self):
        pass

    def compare(self, profile: BehavioralProfileState, current_features: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
        """
        Returns:
            - overall score (0.0 - 100.0)
            - detailed JSON payload summarizing the deviations
        """
        state = profile.get_profile_state()
        
        # If model is barely trained, return 0 deviation impact with "NEW" context
        if state == "NEW":
            return (0.0, {
                "behavioral_deviation": {
                    "available": False,
                    "profile_state": state,
                    "overall_deviation": 0.0,
                    "top_deviations": []
                }
            })
            
        deviations = []
        overall_dev_sum = 0.0
        
        highest_z = 0.0

        for feat, val in current_features.items():
            if feat in profile.statistics:
                s = profile.statistics[feat]
                
                # if variance is essentially 0 because they do the exact same thing (like exactly 0 auth failures)
                # a small epsilon prevents divide by zero.
                std = np.sqrt(s.variance) + 1e-6 
                
                z_score = abs(val - s.mean) / std
                highest_z = max(highest_z, z_score)
                
                # Anything under 2 std deviations is considered normal
                if z_score > 2.0:
                    overall_dev_sum += z_score
                    
                    deviations.append({
                        "feature": feat,
                        "observed": round(val, 2),
                        "baseline": round(s.mean, 2),
                        "deviation": round(z_score, 2)
                    })

        # Score Mapping (Z-score to 0-100)
        # Z-score of 0-2 -> 0. Z-score of 5.0 -> 100
        avg_impact = overall_dev_sum / (len(current_features) + 1e-6)
        raw_score = (min(highest_z, 10.0) / 10.0) * 100.0
        
        if state == "LEARNING":
            raw_score *= 0.5  # Dampen score impact significantly because baseline variance is unstable
            
        final_score = min(100.0, max(0.0, raw_score))

        # Sort deviations highest to lowest
        deviations.sort(key=lambda x: x["deviation"], reverse=True)

        return (final_score, {
            "behavioral_deviation": {
                "available": True,
                "profile_state": state,
                "overall_deviation": round(final_score, 1),
                "max_z_observed": round(highest_z, 2),
                "top_deviations": deviations[:3]
            }
        })
