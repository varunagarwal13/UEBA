import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict, Counter
from analytics.data.spedia.loader import load_spedia_sessions
from analytics.ctmc.population_matrix import load_population_matrix
from analytics.pipeline.analytics_pipeline import AnalyticsPipeline
from analytics.state_extraction.state_extractor import StateExtractor
from analytics.ctmc.ctmc_scorer import CTMCScorer
from analytics.rule_engine.rule_engine import RuleEngine
from analytics.risk_scoring.risk_scorer import RiskScorer


def build_user_matrix(sessions):
    counts = defaultdict(Counter)
    for session in sessions:
        states = [e.get("CTMC_State","") for e in session["events"] if e.get("CTMC_State")]
        for i in range(len(states)-1):
            counts[states[i]][states[i+1]] += 1
    matrix = {}
    for from_s, to_counts in counts.items():
        total = sum(to_counts.values())
        matrix[from_s] = {t: c/total for t,c in to_counts.items()}
    return matrix


def main():
    sessions          = load_spedia_sessions(
        "spedia_anomaly_detection/data/SPEDIA_preprocessed.csv")
    population_matrix = load_population_matrix(
        "spedia_anomaly_detection/data/ctmc_transition_matrix.csv")

    user_sessions = defaultdict(list)
    for s in sessions:
        user_sessions[s["user_id"]].append(s)

    # Build profiles from first 80%
    user_matrices = {}
    user_counts   = {}
    test_sessions = []
    for user, u_sessions in user_sessions.items():
        split = max(1, int(len(u_sessions) * 0.8))
        matrix = build_user_matrix(u_sessions[:split])
        if matrix:
            user_matrices[user] = matrix
            user_counts[user]   = split
        test_sessions.extend(u_sessions[split:])

    # Score every test session but ignore the threshold —
    # collect the raw score for every session
    extractor = StateExtractor()
    ctmc      = CTMCScorer()
    rules     = RuleEngine()
    scorer    = RiskScorer()

    normal_scores    = []
    anomalous_scores = []

    for session in test_sessions:
        user    = session["user_id"]
        states  = extractor.extract_states(session)
        if not states:
            continue

        matrix  = user_matrices.get(user, population_matrix)
        n_train = user_counts.get(user, 0)

        ctmc_score  = ctmc.score(states, matrix, n_train)
        violations  = rules.check_all_rules(states, session["events"])
        result      = scorer.compute(
            user_id=user, session_id=session["session_id"],
            ctmc_score=ctmc_score, violations=violations,
            total_sessions=n_train
        )

        if session.get("anomaly") == 1:
            anomalous_scores.append(result.risk_score)
        else:
            normal_scores.append(result.risk_score)

    # Show score distribution
    print("\n=== Score distribution for NORMAL sessions ===")
    buckets = [0,10,20,30,40,50,60,70,80,90,100]
    for i in range(len(buckets)-1):
        lo, hi = buckets[i], buckets[i+1]
        count  = sum(1 for s in normal_scores if lo <= s < hi)
        bar    = "█" * count
        print(f"  {lo:3d}-{hi:3d} | {bar} {count}")

    print("\n=== Score distribution for ANOMALOUS sessions ===")
    for i in range(len(buckets)-1):
        lo, hi = buckets[i], buckets[i+1]
        count  = sum(1 for s in anomalous_scores if lo <= s < hi)
        bar    = "█" * count
        print(f"  {lo:3d}-{hi:3d} | {bar} {count}")

    print(f"\nNormal   sessions: {len(normal_scores)}  "
          f"avg={sum(normal_scores)/len(normal_scores):.1f}  "
          f"max={max(normal_scores):.1f}")
    print(f"Anomalous sessions: {len(anomalous_scores)}  "
          f"avg={sum(anomalous_scores)/len(anomalous_scores):.1f}  "
          f"max={max(anomalous_scores):.1f}")

    # Find the best threshold
    print("\n=== Precision / Recall at each threshold ===")
    print(f"{'Threshold':>10} {'Alerts':>7} {'TP':>5} {'FP':>5} "
          f"{'FN':>5} {'Prec':>6} {'Recall':>7} {'F1':>6}")
    for threshold in range(5, 95, 5):
        tp = sum(1 for s in anomalous_scores if s >= threshold)
        fp = sum(1 for s in normal_scores    if s >= threshold)
        fn = sum(1 for s in anomalous_scores if s <  threshold)
        prec   = tp/(tp+fp) if (tp+fp) > 0 else 0
        recall = tp/(tp+fn) if (tp+fn) > 0 else 0
        f1     = 2*prec*recall/(prec+recall) if (prec+recall) > 0 else 0
        print(f"{threshold:>10} {tp+fp:>7} {tp:>5} {fp:>5} "
              f"{fn:>5} {prec:>6.2f} {recall:>7.2f} {f1:>6.2f}")


if __name__ == "__main__":
    main()
