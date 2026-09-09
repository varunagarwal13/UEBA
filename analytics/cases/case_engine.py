import uuid
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class CaseEngine:
    """
    V2.1: Resolves independent user alerts into correlated Investigation Cases tracking macro-level attacks.
    """
    
    def __init__(self, time_window_hours: int = 24):
        self.time_window = timedelta(hours=time_window_hours)
        
    def evaluate_alert(self, user_id: str, alert_id: str, alert_score: float, alert_stage: str, alert_time: datetime, open_cases: List[Dict]) -> Dict:
        """
        Takes raw alert and actively open structural Cases for this user.
        Determines whether to attach to existing or create new Case.
        """
        
        # Look for temporally compatible cases
        for case in open_cases:
            last_updated = case.get("updated_at", alert_time)
            
            # Temporal bound Check
            if alert_time - last_updated <= self.time_window:
                # Merge into existing case
                case["alerts"].append(alert_id)
                case["updated_at"] = alert_time
                case["current_stage"] = alert_stage if alert_stage != "UNKNOWN" else case.get("current_stage")
                
                # Boost Case macro risk non-linearly
                case["risk_score"] = min(100.0, case["risk_score"] + (alert_score * 0.2))
                
                if case["risk_score"] >= 85.0:
                    case["severity"] = "Critical"
                elif case["risk_score"] >= 65.0:
                    case["severity"] = "High"
                    
                # Update dynamic summary
                case["summary"] = f"User {user_id} generated {len(case['alerts'])} correlated alerts peaking at stage {case['current_stage']}."
                return case
                
        # If no temporal matches, generate brand new case
        new_case = {
            "case_id": f"CAS-{str(uuid.uuid4())[:8].upper()}",
            "user_id": user_id,
            "status": "OPEN",
            "risk_score": alert_score, # Baseline it at the triggering alert's severity
            "severity": "Critical" if alert_score >= 85 else "High" if alert_score >= 65 else "Medium",
            "current_stage": alert_stage,
            "alerts": [alert_id],
            "created_at": alert_time,
            "updated_at": alert_time,
            "summary": f"User {user_id} triggered a new isolated case linked to {alert_stage} anomalies."
        }
        
        return new_case
