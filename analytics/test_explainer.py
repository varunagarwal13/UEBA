import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
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
    sessions  = load_spedia_sessions(
        "spedia_anomaly_detection/data/SPEDIA_preprocessed.csv")
    pop_matrix = load_population_matrix(
        "spedia_anomaly_detection/data/ctmc_transition_matrix.csv")
    pipeline   = AnalyticsPipeline(pop_matrix)

    user_sessions = defaultdict(list)
    for s in sessions:
        user_sessions[s["user_id"]].append(s)

    for user, u_sessions in user_sessions.items():
        split = max(1, int(len(u_sessions) * 0.8))
        matrix = build_user_matrix(u_sessions[:split])
        if matrix:
            pipeline.user_matrices[user]       = matrix
            pipeline.user_session_counts[user] = split

    # Find first 3 alerts and print full explanation
    found = 0
    for user, u_sessions in user_sessions.items():
        split = max(1, int(len(u_sessions) * 0.8))
        for session in u_sessions[split:]:
            if session.get("anomaly") != 1:
                continue
            result = pipeline.process_session(session)
            if not result:
                continue

            print("\n" + "=" * 60)
            print(f"ALERT: {result['alert']['alert_id']}")
            print(f"User:  {result['alert']['user_id']}")
            print(f"Score: {result['alert']['risk_score']} "
                  f"({result['alert']['severity']})")
            print(f"Confidence: {result['alert']['confidence']}")

            print(f"\n--- SUMMARY ---")
            print(result["explanation"]["summary"])

            print(f"\n--- REASONS ({len(result['explanation']['reasons'])}) ---")
            for i, reason in enumerate(result["explanation"]["reasons"], 1):
                print(f"  {i}. {reason}")

            print(f"\n--- COMPACT TIMELINE ---")
            for step in result["timeline"]["timeline_compact"]:
                print(f"  → {step}")

            print(f"\n--- RISK CONTEXT ---")
            print(result["explanation"]["risk_context"])

            print(f"\n--- DETECTION METHODS ---")
            for m in result["explanation"]["detection_methods"]:
                print(f"  • {m}")

            print(f"\n--- RECOMMENDED ACTIONS ---")
            for i, action in enumerate(
                    result["explanation"]["recommended_actions"], 1):
                print(f"  {i}. {action}")

            found += 1
            if found >= 3:
                return


if __name__ == "__main__":
    main()
