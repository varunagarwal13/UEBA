import os
import json
import pandas as pd
import numpy as np
import pickle
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, roc_auc_score, average_precision_score, confusion_matrix, precision_score, recall_score, f1_score

from analytics.data.spedia.loader import load_spedia_sessions
from analytics.pipeline.feature_extractor import FeatureExtractor

def calc_top_k(scores, labels, k_list):
    res = {}
    sorted_idx = np.argsort(scores)[::-1]
    sorted_labels = labels[sorted_idx]
    
    total_anomalies = np.sum(labels)
    if total_anomalies == 0: total_anomalies = 1
    
    for k in k_list:
        k_labels = sorted_labels[:k]
        tp = np.sum(k_labels)
        res[f"Precision@{k}"] = float(tp / k)
        res[f"Recall@{k}"] = float(tp / total_anomalies)
    return res

def train_and_evaluate():
    print("Loading sessions...")
    dataset_path = "spedia_anomaly_detection/data/SPEDIA_preprocessed.csv"
    raw_sessions = load_spedia_sessions(dataset_path)

    print("Extracting clean mathematical features (Zero target leakage)...")
    extractor = FeatureExtractor()
    features_list = []
    
    for s in raw_sessions:
        feat = extractor.extract_features(s)
        feat["session_id"] = s["session_id"]
        feat["Anomaly"] = s["anomaly"]  
        
        timestamps = [e.get("timestamp") for e in s["events"] if e.get("timestamp")]
        feat["start_time"] = min(timestamps) if timestamps else "2025-03-01T00:00:00Z"
        features_list.append(feat)

    df = pd.DataFrame(features_list)
    df["start_time"] = pd.to_datetime(df["start_time"], format='mixed', utc=True)
    df = df.sort_values("start_time").reset_index(drop=True)

    print("\nExecuting Chronological Split (Phase 4)...")
    train_mask = df["start_time"] < "2025-03-21"
    val_mask   = (df["start_time"] >= "2025-03-21") & (df["start_time"] < "2025-03-26")
    test_mask  = df["start_time"] >= "2025-03-26"
    
    df_train, df_val, df_test = df[train_mask].copy(), df[val_mask].copy(), df[test_mask].copy()
    
    feature_cols = extractor.feature_names
    X_train, X_val, X_test = df_train[feature_cols].values, df_val[feature_cols].values, df_test[feature_cols].values
    y_val, y_test = df_val["Anomaly"].values, df_test["Anomaly"].values

    print("\nTraining Isolation Forest cleanly on X_train...")
    clf = IsolationForest(n_estimators=100, random_state=42)
    clf.fit(X_train)

    os.makedirs("analytics/models", exist_ok=True)
    with open("analytics/models/if_model.pkl", "wb") as f:
        pickle.dump(clf, f)

    print("\nTuning threshold on VALIDATION set...")
    val_raw_scores = -1.0 * clf.decision_function(X_val)
    best_f1, best_thresh = 0, 0
    for pct in np.linspace(50, 99, 50):
        thresh = np.percentile(val_raw_scores, pct)
        val_preds = (val_raw_scores > thresh).astype(int)
        f = f1_score(y_val, val_preds, zero_division=0)
        if f > best_f1:
            best_f1 = f
            best_thresh = thresh
            
    print(f"Chosen Validation Threshold: {best_thresh:.4f} (Val F1: {best_f1:.4f})")

    print("\nEvaluating on untouched TEST set...")
    test_raw_scores = -1.0 * clf.decision_function(X_test)
    y_pred = (test_raw_scores > best_thresh).astype(int)
    
    pr_auc = average_precision_score(y_test, test_raw_scores)
    roc_auc = roc_auc_score(y_test, test_raw_scores)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    
    top_k_res = calc_top_k(test_raw_scores, y_test, [10, 25, 50])

    metrics = {
        "train_sessions": len(X_train),
        "validation_sessions": len(X_val),
        "test_sessions": len(X_test),
        "anomaly_prevalence": float(np.mean(y_test)),
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "fpr": float(fpr),
        "confusion_matrix": {"TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp)},
        "average_precision": float(pr_auc),
        "threshold_used": float(best_thresh)
    }
    metrics.update(top_k_res)

    os.makedirs("analytics/evaluation", exist_ok=True)
    with open("analytics/evaluation/if_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    os.makedirs("docs", exist_ok=True)
    with open("docs/IF_EVALUATION.md", "w") as f:
        f.write("# Isolation Forest Evaluation Report\n\n")
        f.write(f"- Train Sessions (Mar 6-20): {metrics['train_sessions']}\n")
        f.write(f"- Valid Sessions (Mar 21-25): {metrics['validation_sessions']}\n")
        f.write(f"- Test Sessions (Mar 26-30): {metrics['test_sessions']}\n")
        f.write(f"- Anomaly Prevalence: {metrics['anomaly_prevalence']:.4f}\n\n")
        f.write(f"### Core Metrics (Threshold = {best_thresh:.4f})\n")
        f.write(f"- **Precision:** {precision:.4f}\n- **Recall:** {recall:.4f}\n- **F1 Score:** {f1:.4f}\n- **PR-AUC:** {pr_auc:.4f}\n- **FPR:** {fpr:.4f}\n\n")
        f.write(f"### Top-K SOC Ranking\n")
        for k in [10, 25, 50]:
            f.write(f"- **Precision@{k}:** {metrics[f'Precision@{k}']:.4f} | **Recall@{k}:** {metrics[f'Recall@{k}']:.4f}\n")

if __name__ == "__main__":
    train_and_evaluate()
