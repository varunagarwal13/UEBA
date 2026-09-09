from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class AttackStage:
    stage_name: str
    evidence: str
    timestamp: str  
    confidence: float

class AttackStageInference:
    """
    Maps concrete session evidence to attack chains without fabricating
    classifications purely from mathematical rule counts.
    """
    
    def infer_stages(self, session: Dict[str, Any]) -> List[AttackStage]:
        events = session.get("events", [])
        stages = []
        
        # Sort events by timestamp inside session to ensure correct ordering analysis
        try:
            sorted_events = sorted(events, key=lambda x: x.get("timestamp", ""))
        except:
            sorted_events = events
            
        has_escalation = False
        
        for e in sorted_events:
            state = e.get("CTMC_State")
            ts = e.get("timestamp", "unknown")
            action = e.get("Action", "")
            
            # 1. Discovery / Recon
            if state == "Recon_Command":
                stages.append(AttackStage(
                    stage_name="Discovery",
                    evidence=f"Reconnaissance logic detected: {action}",
                    timestamp=ts,
                    confidence=0.85
                ))
                
            # 2. Privilege Escalation
            elif state == "Privilege_Command":
                has_escalation = True
                stages.append(AttackStage(
                    stage_name="Privilege Escalation",
                    evidence=f"User escalated credentials or ran privileged tool: {action}",
                    timestamp=ts,
                    confidence=0.95
                ))
                
            # 3. Collection
            elif state in ("File_Access", "File_Modify") and has_escalation:
                stages.append(AttackStage(
                    stage_name="Collection",
                    evidence=f"Access to files immediately following privilege escalation",
                    timestamp=ts,
                    confidence=0.75
                ))
                
            # 4. Exfiltration (Note: A deeper exfil score exists in Communication Analytics)
            elif state == "Email" and float(e.get("Attachments", 0)) > 0:
                stages.append(AttackStage(
                    stage_name="Exfiltration",
                    evidence="Outbound email communication containing data attachments",
                    timestamp=ts,
                    confidence=0.60
                ))
                
        # Deduplicate stages while preserving sequence
        seen = set()
        deduped = []
        for s in stages:
            if s.stage_name not in seen:
                seen.add(s.stage_name)
                deduped.append(s)
                
        return deduped
