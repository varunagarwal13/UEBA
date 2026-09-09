import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from analytics.network.network_pipeline import NetworkPipeline

def test_network_pipeline_disabled_status():
    pipe = NetworkPipeline()
    assert pipe.is_active == True

def test_network_pipeline_large_flow():
    pipe = NetworkPipeline()
    # Extremely large payload over non-standard port
    flow = {
        "src_ip": "192.168.1.1",
        "dst_ip": "8.8.8.8",
        "protocol": "TCP",
        "bytes_sent": 50000000
    }
    result = pipe.process_flow(flow)
    assert result is not None
    assert result["alert_found"] == True
    assert result["risk_score_delta"] == 45.0

def test_network_pipeline_normal_flow():
    pipe = NetworkPipeline()
    # Normal HTTPS traffic
    flow = {
        "src_ip": "192.168.1.1",
        "dst_ip": "8.8.8.8",
        "protocol": "HTTPS",
        "bytes_sent": 50000000
    }
    result = pipe.process_flow(flow)
    assert result is None
