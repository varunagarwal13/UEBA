import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict, Counter
from analytics.data.spedia.loader import load_spedia_sessions
from analytics.ctmc.population_matrix import load_population_matrix
from analytics.pipeline.analytics_pipeline import AnalyticsPipeline


def build_user_matrix(sessions):
    counts = defaultdict(Counter)
    for session in sessions:
        states = [e.get("CTMC_State","") for e in session["events"]
                  if e.get("CTMC_State")]
        for i in range(len(states)-1):
            counts[states[i]][states[i+1]] += 1
    matrix = {}
    for from_s, to_counts in counts.items():
        total = sum(to_counts.values())
        matrix[from_s] = {t: c/total for t,c in to_counts.items()}
    return matrix


def main():
    PREPROCESSED = "spedia_anomaly_detection/data/SPEDIA_preprocessed.csv"
    MATRIX_CSV   = "spedia_anomaly_detection/data/ctmc_transition_matrix.csv"

    sessions          = load_spedia_sessions(PREPROCESSED)
    population_matrix = load_population_matrix(MATRIX_CSV)
    pipeline          = AnalyticsPipeline(population_matrix)

    user_sessions = defaultdict(list)
    for s in sessions:
        user_sessions[s["user_id"]].append(s)

    print("=" * 55)
    print("UEBA Analytics Pipeline — Full Evaluation")
    print("=" * 55)

    test_sessions = []
    print(f"\nBuilding personal behavioral profiles...")
    for user, u_sessions in user_sessions.items():
        split  = max(1, int(len(u_sessions) * 0.8))
        matrix = build_user_matrix(u_sessions[:split])
        if matrix:
            pipeline.user_matrices[user]       = matrix
            pipeline.user_session_counts[user] = split
            print(f"  {user}: profile built from {split} sessions")
        test_sessions.extend(u_sessions[split:])

    total_sessions = sum(len(v) for v in user_sessions.values())
    print(f"\nTotal sessions : {total_sessions}")
    print(f"Test           : {len(test_sessions)} sessions")
    print(f"\nScoring {len(test_sessions)} test sessions...")

    alerts = []
    tp = fp = tn = fn = 0

    for session in test_sessions:
        result       = pipeline.process_session(session)
        ground_truth = session.get("anomaly", 0)
        if result:
            alerts.append((session, result))
            if ground_truth == 1: tp += 1
            else:                 fp += 1
        else:
            if ground_truth == 0: tn += 1
            else:                 fn += 1

    precision = tp/(tp+fp) if (tp+fp) > 0 else 0
    recall    = tp/(tp+fn) if (tp+fn) > 0 else 0
    f1        = 2*precision*recall/(precision+recall) if (precision+recall) > 0 else 0

    print(f"\n{'=' * 55}")
    print(f"Evaluation Results ({len(test_sessions)} test sessions)")
    print(f"{'=' * 55}")
    print(f"Anomalous sessions in test set : {tp+fn}")
    print(f"Alerts generated               : {len(alerts)}")
    print(f"True Positives  (caught threats)   : {tp}")
    print(f"False Positives (false alarms)     : {fp}")
    print(f"True Negatives  (correct silence)  : {tn}")
    print(f"False Negatives (missed threats)   : {fn}")
    print(f"Precision : {precision:.2f}")
    print(f"Recall    : {recall:.2f}")
    print(f"F1 Score  : {f1:.2f}")
    print(f"{'=' * 55}")

    if alerts:
        print("\nTop 5 alerts by risk score:")
        alerts.sort(key=lambda x: x[1]["alert"]["risk_score"], reverse=True)
        for session, alert_data in alerts[:5]:
            a  = alert_data["alert"]
            b  = alert_data["model_breakdown"]
            gt = session.get("anomaly","?")
            tag = "CORRECT" if gt == 1 else "FALSE ALARM"
            print(f"\n  [{tag}] {a['user_id']} | {a['severity']} | "
                  f"Score:{a['risk_score']} | CTMC:{b['ctmc_score']} | "
                  f"Rules:{b['rule_score']} | Conf:{a['confidence']}")
            for v in b["rule_violations"]:
                print(f"    [{v['rule_id']}] {v['rule_name']}")

    print("\nDone.")


if __name__ == "__main__":
    main()
