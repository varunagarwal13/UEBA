from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class ExfiltrationDetection:
    evidence: List[str]
    sequence_detected: bool
    contributing_event_ids: List[str]
    confidence: float
    score: float

class CommunicationAnalytics:
    """
    Application-Level Communication & Exfiltration Detector.
    *NOTE: This is intentionally distinct from full Network UEBA, which
    would require low-level NetFlow/Packet/IP telemetry unavailable in SPEDIA.*
    """

    def __init__(self):
        # We classify specific external domains as higher risk.
        self.suspicious_external_domains = ["gmail.com", "yahoo.com", "protonmail.com", "dropbox.com"]

    def analyze_session(self, session: Dict[str, Any]) -> ExfiltrationDetection:
        events = session.get("events", [])
        
        evidence = []
        contributing_ids = []
        
        has_file_access = False
        has_staging = False
        has_suspicious_comms = False
        
        total_transfer_size = 0.0
        
        for e in events:
            state = e.get("CTMC_State")
            evt_id = e.get("event_id")
            
            # 1. Collection Stage
            if state in ("File_Access", "File_Modify"):
                has_file_access = True
                
            # 2. Staging Stage
            if state == "File_Add" and has_file_access:
                has_staging = True
                evidence.append("Data staged (File_Add) following File_Access")
                if evt_id: contributing_ids.append(evt_id)
                
            # 3. Communication / Exfil Stage (Email/Web)
            if state == "Email":
                recipients = str(e.get("To", "")) + " " + str(e.get("Cc", "")) + " " + str(e.get("Bcc", ""))
                recipients = recipients.lower()
                
                # Check external recipient evidence
                is_external = any(domain in recipients for domain in self.suspicious_external_domains)
                has_attachment = float(e.get("Attachments") or 0.0) > 0
                
                if is_external:
                    has_suspicious_comms = True
                    evidence.append(f"Email sent to external/suspicious recipient: {recipients.strip()}")
                    if evt_id: contributing_ids.append(evt_id)
                if has_attachment:
                    has_suspicious_comms = True
                    evidence.append("Email sent with attachments")
                    total_transfer_size += float(e.get("Size") or 0.0)
                    if evt_id: contributing_ids.append(evt_id)
            
            if state == "Browser" and e.get("Url"):
                url = str(e.get("Url")).lower()
                if any(domain in url for domain in self.suspicious_external_domains):
                    has_suspicious_comms = True
                    evidence.append(f"Suspicious external URL accessed: {url}")
                    if evt_id: contributing_ids.append(evt_id)

        # Calculate chronological sequence pattern (Access -> Stage -> Transfer)
        sequence_detected = has_file_access and has_suspicious_comms
        
        # Calculate Risk Score (0-100)
        score = 0.0
        confidence = 0.0
        
        if sequence_detected:
            score = 60.0 # Base sequence penalty
            confidence = 0.70
            
            if has_staging:
                score += 25.0
                confidence = 0.90
                evidence.insert(0, "High-Confidence Exfiltration: Source Data -> Staging -> External Transfer")
                
            if total_transfer_size > 10 * 1024 * 1024:  # 10MB heuristic
                score += 15.0
                evidence.append(f"Large volume transfer detected: {total_transfer_size/1024/1024:.1f} MB")
        
        elif has_suspicious_comms:
            # Transfer without collection in same session 
            score = 30.0
            confidence = 0.50
            evidence.append("External communication detected without prior data staging in same session (Medium Confidence).")

        return ExfiltrationDetection(
            evidence=list(set(evidence)),
            sequence_detected=sequence_detected,
            contributing_event_ids=list(set(contributing_ids)),
            confidence=confidence,
            score=min(100.0, score)
        )
