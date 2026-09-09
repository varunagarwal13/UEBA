from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from analytics.rule_engine.rule_engine import RuleViolation
import json

@dataclass
class Explanation:
    alert_id: str
    summary: str
    reasons: List[str]
    recommended_actions: List[str]
    risk_context: str

class Explainer:
    """
    V2.1 Explainability Module: Explicitly details What Happened, Why It Is Abnormal,
    and Which Models Agree without fabricating missing constraints.
    """
    
    def explain(
        self,
        alert_id: str,
        user_id: str,
        risk_score: float,
        severity: str,
        confidence: float,
        violations: List[RuleViolation],
        state_sequence: List[str],
        ctmc_score: Optional[float],
        rule_score: Optional[float],
        if_score: Optional[float],
        pb_score: Optional[float],
        attack_score: Optional[float],
        dev_json: Dict[str, Any],
        attack_stage: str
    ) -> Explanation:
        
        reasons = []
        actions = []
        
        # WHAT HAPPENED & WHY ABNORMAL
        summary = f"User {user_id} triggered a {severity} severity alert (Risk: {risk_score:.1f}, Confidence: {confidence:.2f}). "
        
        if attack_stage and attack_stage != "UNKNOWN":
            summary += f"The activity maps to the {attack_stage} attack stage. "
            
        # WHICH MODELS AGREE
        agreement_desc = []
        if ctmc_score is not None:
            tier = "HIGH" if ctmc_score > 70 else "MEDIUM" if ctmc_score > 40 else "LOW"
            agreement_desc.append(f"CTMC: {tier} ({ctmc_score:.1f})")
        else:
            agreement_desc.append("CTMC: UNAVAILABLE")
            
        if if_score is not None:
            tier = "HIGH" if if_score > 70 else "MEDIUM" if if_score > 40 else "LOW"
            agreement_desc.append(f"Isolation Forest: {tier} ({if_score:.1f})")
        else:
            agreement_desc.append("Isolation Forest: UNAVAILABLE (Missing Artifact)")
            
        if rule_score is not None:
            tier = "HIGH" if rule_score > 70 else "MEDIUM" if rule_score > 40 else "LOW"
            agreement_desc.append(f"Rules: {tier} ({rule_score:.1f})")
            
        if attack_score is not None:
            tier = "HIGH" if attack_score > 70 else "MEDIUM" if attack_score > 40 else "LOW"
            agreement_desc.append(f"Attack Chain: {tier} ({attack_score:.1f})")
        else:
            agreement_desc.append("Attack Chain: UNAVAILABLE")
            
        b_dev = dev_json.get("behavioral_deviation", {})
        if b_dev.get("available"):
            state = b_dev.get("profile_state")
            top = b_dev.get("top_deviations", [])
            tier = "HIGH" if pb_score and pb_score > 70 else "LOW"
            agreement_desc.append(f"Behavioral Deviation: {tier} ({state})")
            
            if top:
                feat = top[0]
                reasons.append(f"Current session was {feat['deviation']} standard deviations above normal for {feat['feature']}.")
            else:
                reasons.append("Current session exhibited bounded deviations against statistical profile.")
        else:
            agreement_desc.append(f"Behavioral Deviation: UNAVAILABLE (Profile is NEW)")

        if violations:
            reasons.append(f"Violated {len(violations)} explicit security rules (e.g., {violations[0].rule_name}).")
            actions.append("Review manual rule trigger anomalies in SIEM.")
            
        context = "Model Agreement Breakdown: " + " | ".join(agreement_desc)
        
        actions.append(f"Review user's {attack_stage} sequence.")
        if severity in ["Critical", "High"]:
            actions.append("Consider immediate temporary credential suspension pending review.")
            
        return Explanation(
            alert_id=alert_id,
            summary=summary,
            reasons=reasons,
            recommended_actions=actions,
            risk_context=context
        )
