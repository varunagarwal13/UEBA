from typing import Dict, List, Any
import numpy as np
from dataclasses import dataclass

@dataclass
class TrendResult:
    moving_average: float
    velocity: float
    acceleration: float
    is_sudden_spike: bool
    repeated_high_risk: bool
    trend_score: float # 0-100 representation of historical danger

class RiskTrendManager:
    """
    Stateful engine investigating the chronological velocity of risk.
    Rejects simple average risk in favor of momentum equations.
    """
    
    def __init__(self):
        # Maps user_id -> List of historical Risk Scores (0-100)
        self.user_history: Dict[str, List[float]] = {}
        
    def analyze_and_update(self, user_id: str, current_risk: float) -> TrendResult:
        history = self.user_history.get(user_id, [])
        
        ma = 0.0
        vel = 0.0
        accel = 0.0
        spike = False
        repeated_high = False
        trend_score = 0.0
        
        if len(history) > 0:
            ma = float(np.mean(history[-5:])) # Short term 5-session rolling average
            vel = current_risk - history[-1]
            
            if len(history) > 1:
                prev_vel = history[-1] - history[-2]
                accel = vel - prev_vel
                
            # Sudden Spike: e.g. User average is 10, suddenly hits 85
            if ma < 30 and current_risk > 70:
                spike = True
                
            # Repeated high risk: The last 3 sessions were all above 60
            if len(history) >= 2 and all(r > 60 for r in history[-2:]) and current_risk > 60:
                repeated_high = True
                
            # Compute a continuous Trend Score penalty (max 30 points added to a master fusion score)
            if spike:
                trend_score += 25.0
            if repeated_high:
                trend_score += 30.0
            if vel > 40: # Rapid escalation
                trend_score += 15.0
                
        # Must update sequentially AFTER calculation to prevent data leakage
        if user_id not in self.user_history:
            self.user_history[user_id] = []
        self.user_history[user_id].append(current_risk)
        
        # Prune long histories
        if len(self.user_history[user_id]) > 50:
            self.user_history[user_id].pop(0)
            
        return TrendResult(
            moving_average=ma,
            velocity=vel,
            acceleration=accel,
            is_sudden_spike=spike,
            repeated_high_risk=repeated_high,
            trend_score=min(100.0, trend_score)
        )
