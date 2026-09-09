from analytics.attack_chain.attack_stage import AttackStage
from typing import Dict, Any, List

class StageMapper:
    """Maps deterministic engine outcomes/rules/CTMC states to explicit Stage Continnums"""
    
    @staticmethod
    def map_session(session: Dict[str, Any], active_rules: List[str]) -> AttackStage:
        action = str(session.get("action", "")).lower()
        event_type = str(session.get("event_type", "")).lower()
        
        # 1. Highest Priority: Explicit Rule Violations
        if "mass file exfil" in str(active_rules).lower():
            return AttackStage.EXFILTRATION
        if "single-state" in str(active_rules).lower() and "login" in action:
            return AttackStage.AUTHENTICATION
            
        # 2. Activity Type Heuristics
        if event_type == "login" or "auth:failure" in action:
            return AttackStage.AUTHENTICATION
            
        recon_commands = ["whoami", "id", "ps", "netstat", "ipconfig"]
        if any(c in action for c in recon_commands):
            return AttackStage.RECONNAISSANCE
            
        priv_commands = ["sudo", "su", "chmod -r 777", "chown"]
        if any(c in action for c in priv_commands):
            return AttackStage.PRIVILEGE_ESCALATION
            
        if event_type == "file_access" and "read" in action:
            return AttackStage.COLLECTION
            
        if "zip" in action or "tar" in action or ".rar" in action:
            return AttackStage.STAGING
            
        if event_type == "email" and "attachment" in action:
            return AttackStage.EXFILTRATION
            
        if "crontab" in action or "schtasks" in action:
            return AttackStage.PERSISTENCE
            
        return AttackStage.UNKNOWN
