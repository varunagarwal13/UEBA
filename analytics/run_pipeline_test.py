import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict, Counter
from analytics.data.spedia.loader import load_spedia_sessions
from analytics.ctmc.population_matrix import load_population_matrix
from analytics.pipeline.analytics_pipeline import AnalyticsPipeline


def build_user_transition_matrix(sessions):
    """
    Builds a personal transition matrix for one user
    from their historical (training) sessions.

    How it works:
    - We look at every consecutive pair of states in every session
    - We count how many times each (from_state -> to_state) pair occurs
    - We divide each count by the row total to get probabilities
    - Result: a dict like {"Login": {"Browser": 0.6, "Command": 0.4}, ...}
    """
    counts = defaultdict(Counter)

    for session in sessions:
        states = [e.get("CTMC_State", "") for e in session["events"] if e.get("CTMC_State")]
        for i in range(len(states) - 1):
            counts[states[i]][states[i+1]] += 1

    # Convert counts to probabilities
    matrix = {}
    for from_state, to_counts in counts.items():
        total = sum(to_counts.values())
        matrix[from_state] = {
            to_state: count / total
            for to_state, count in to_counts.items()
        }
    return matrix


def main():
    PREPROCESSED = "spedia_anomaly_detection/data/SPEDIA_preprocessed.csv"
    MATRIX_CSV   = "spedia_anomaly_detection/data/ctmc_transition_matrix.csv"

    sessions          = load_spedia_sessions(PREPROCESSED)
    population_matrix = load_population_matrix(MATRIX_CSV)
    pipeline          = AnalyticsPipeline(population_matrix)

    # --- Step 1: Group sessions by user ---
    user_sessions = defaultdict(list)
    for s in sessions:
        user_sessions[s["user_id"]].append(s)

    # --- Step 2: For each user, use first 80% to build profile,
    #             score the remaining 20% ---
    print("=" * 55)
    print("UEBA Analytics Pipeline — Full Evaluation")
    print("=" * 55)

    train_sessions = []
    test_sessions  = []

    for user, u_sessions in user_sessions.items():
        split = max(1, int(len(u_sessions) * 0.8))
        train_sessions.extend(u_sessions[:split])
        test_sessions.extend(u_sessions[split:])

    print(f"\nTotal sessions : {len(sessions)}")
    print(f"Training       : {len(train_sessions)} sessions (build profiles)")
    print(f"Test           : {len(test_sessions)} sessions (score these)")

    # --- Step 3: Build personal transition matrices from training data ---
    print("\nBuilding personal behavioral profiles...")
    for user, u_sessions in user_sessions.items():
        split  = max(1, int(len(u_sessions) * 0.8))
        train  = u_sessions[:split]
        matrix = build_user_transition_matrix(train)
        if matrix:
            pipeline.user_matrices[user]        = matrix
            pipeline.user_session_counts[user]  = len(train)
            print(f"  {user}: profile built from {len(train)} sessions")

    # --- Step 4: Score test sessions ---
    print(f"\nScoring {len(test_sessions)} test sessions...")

    alerts       = []
    true_pos     = 0   # alert fired, session IS anomalous (correct)
    false_pos    = 0   # alert fired, session is normal (wrong)
    true_neg     = 0   # no alert, session is normal (correct)
    false_neg    = 0   # no alert, session IS anomalous (missed)

    for session in test_sessions:
        result    = pipeline.process_session(session)
        ground_truth = session.get("anomaly", 0)

        if result:
            alerts.append((session, result))
            if ground_truth == 1:
                true_pos += 1
            else:
                false_pos += 1
        else:
            if ground_truth == 0:
                true_neg += 1
            else:
                false_neg += 1

    # --- Step 5: Print evaluation metrics ---
    total = len(test_sessions)
    anomalous_in_test = sum(1 for s in test_sessions if s.get("anomaly") == 1)

    precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) > 0 else 0
    recall    = true_pos / (true_pos + false_neg) if (true_pos + false_neg) > 0 else 0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0)

    print(f"\n{'=' * 55}")
    print(f"Evaluation Results ({total} test sessions)")
    print(f"{'=' * 55}")
    print(f"Anomalous sessions in test set : {anomalous_in_test}")
    print(f"Alerts generated               : {len(alerts)}")
    print(f"")
    print(f"True Positives  (caught threats)   : {true_pos}")
    print(f"False Positives (false alarms)     : {false_pos}")
    print(f"True Negatives  (correct silence)  : {true_neg}")
    print(f"False Negatives (missed threats)   : {false_neg}")
    print(f"")
    print(f"Precision : {precision:.2f}  (of alerts fired, how many were real)")
    print(f"Recall    : {recall:.2f}  (of real threats, how many we caught)")
    print(f"F1 Score  : {f1:.2f}  (balance of precision and recall)")
    print(f"{'=' * 55}")

    if alerts:
        print("\nTop 5 alerts by risk score:")
        alerts.sort(key=lambda x: x[1]["alert"]["risk_score"], reverse=True)
        for session, alert_data in alerts[:5]:
            a  = alert_data["alert"]
            b  = alert_data["model_breakdown"]
            gt = session.get("anomaly", "?")
            correct = "CORRECT" if gt == 1 else "FALSE ALARM"
            print(f"\n  [{correct}] {a['user_id']} | {a['severity']} | "
                  f"Score:{a['risk_score']} | CTMC:{b['ctmc_score']} | "
                  f"Rules:{b['rule_score']} | Confidence:{a['confidence']}")
            for v in b["rule_violations"]:
                print(f"    [{v['rule_id']}] {v['rule_name']}")


if __name__ == "__main__":
    main()
