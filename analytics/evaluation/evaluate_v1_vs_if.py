import os
import json
import pandas as pd
import pickle

from analytics.data.spedia.loader import load_spedia_sessions
from analytics.pipeline.feature_extractor import FeatureExtractor

def benchmark():
    with open("analytics/evaluation/if_metrics.json", "r") as f:
        metrics = json.load(f)
    thresh = metrics["threshold_used"]

    print("Loading test sessions...")
    dataset_path = "spedia_anomaly_detection/data/SPEDIA_preprocessed.csv"
    raw_sessions = load_spedia_sessions(dataset_path)

    extractor = FeatureExtractor()
    test_data = []

    for s in raw_sessions:
        timestamps = [e.get("timestamp") for e in s["events"] if e.get("timestamp")]
        start_time = min(timestamps) if timestamps else "2025-03-01T00:00:00Z"
        if start_time < "2025-03-26":
            continue
        
        feat = extractor.extract_features(s)
        feat["session_id"] = s["session_id"]
        feat["Anomaly"] = s["anomaly"]
        feat["V1_Risk_Score"] = s["events"][0]["Risk_Score"] if "Risk_Score" in s["events"][0] else 0
        test_data.append(feat)

    df_test = pd.DataFrame(test_data)
    X_test = df_test[extractor.feature_names].values
    
    with open("analytics/models/if_model.pkl", "rb") as f:
        clf = pickle.load(f)

    # Use raw score for negative threshold logic -> higher score is more negative/normal.
    test_raw_scores = -1.0 * clf.decision_function(X_test)
    df_test["if_pred"] = (test_raw_scores > thresh).astype(int)
    df_test["v1_pred"] = (df_test["V1_Risk_Score"] >= 70.0).astype(int)

    both = len(df_test[(df_test["v1_pred"] == 1) & (df_test["if_pred"] == 1)])
    neither = len(df_test[(df_test["v1_pred"] == 0) & (df_test["if_pred"] == 0)])
    v1_only = len(df_test[(df_test["v1_pred"] == 1) & (df_test["if_pred"] == 0)])
    if_only = len(df_test[(df_test["v1_pred"] == 0) & (df_test["if_pred"] == 1)])

    if_only_anomalies = len(df_test[(df_test["v1_pred"] == 0) & (df_test["if_pred"] == 1) & (df_test["Anomaly"] == 1)])
    if_only_rate = (if_only_anomalies / if_only) if if_only > 0 else 0

    res = {
        "test_sessions": len(df_test),
        "both_detected": both,
        "v1_missed_if_detected": if_only,
        "if_missed_v1_detected": v1_only,
        "neither_detected": neither,
        "if_only_anomaly_rate": float(if_only_rate)
    }

    os.makedirs("analytics/evaluation", exist_ok=True)
    with open("analytics/evaluation/v1_vs_if.json", "w") as f:
        json.dump(res, f, indent=2)

    os.makedirs("docs", exist_ok=True)
    with open("docs/V1_VS_IF_BENCHMARK.md", "w") as f:
        f.write("# V1 vs Isolation Forest Benchmark\n")
        f.write(f"- Test Sessions Chronological Sub-Matrix: {len(df_test)}\n\n")
        f.write(f"### Disagreement Analysis\n")
        f.write(f"- Both Detected: {both}\n")
        f.write(f"- Neither Detected: {neither}\n")
        f.write(f"- IF ONLY (V1 Missed): {if_only}\n")
        f.write(f"- V1 ONLY (IF Missed): {v1_only}\n\n")
        f.write(f"### Efficacy Rate\n")
        f.write(f"Of the {if_only} sessions that **only** IF flagged, {if_only_rate * 100:.1f}% were verified true anomalies bypassing static logic.\n")

if __name__ == "__main__":
    benchmark()
