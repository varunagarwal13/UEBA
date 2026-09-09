from typing import Dict, Any, Optional

class NetworkPipeline:
    """
    NETWORK UEBA STATUS: DISABLED — DATASET LIMITATION

    The primary SPEDIA dataset strictly provides host/application-level 
    telemetry (e.g. Email Attachment bytes, HTTP URL domains). True low-level 
    network flow analytics (TCP/UDP, Packet payloads, src/dst port correlation) 
    are unavailable natively.

    This class serves as a clean, standardized architectural extension point to process
    network-specific features strictly separate from behavioral Application UEBA.
    """
    def __init__(self):
        # We could load a separate Network Isolation Forest here in the future
        self.is_active = True

    def process_flow(self, network_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Receives raw network flow events ingested from `/logs/network`.
        """
        src_ip = network_event.get("src_ip", "0.0.0.0")
        dst_ip = network_event.get("dst_ip", "0.0.0.0")
        protocol = str(network_event.get("protocol", "UNKNOWN")).upper()
        bytes_sent = int(network_event.get("bytes_sent", 0))

        # -----------------------------------------------------
        # Application vs Network Boundary Context Checks
        # -----------------------------------------------------
        
        # 1. Simple heuristic check (e.g. massive data over unknown protocol)
        if bytes_sent > 10000000 and protocol not in ["HTTPS", "HTTP", "SMB"]:
            return {
                "alert_found": True,
                "reason": f"Suspicious large flow ({bytes_sent} bytes) over {protocol} from {src_ip}",
                "risk_score_delta": 45.0
            }

        # 2. Mock IP reputation check
        if dst_ip.startswith("9.") or src_ip.startswith("100."):
            return {
                "alert_found": True,
                "reason": f"Communication detected with known untrusted subnet ({dst_ip})",
                "risk_score_delta": 25.0
            }

        return None
