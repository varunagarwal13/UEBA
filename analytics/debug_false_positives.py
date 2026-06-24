import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict, Counter
from analytics.data.spedia.loader import load_spedia_sessions
from analytics.ctmc.population_matrix import load_population_matrix
from analytics.state_extraction.state_extractor import StateExtractor
from analytics.ctmc.ctmc_scorer import CTMCScorer
from analytics.rule_engine.rule_engine import RuleEngine
from analytics.risk_scoring.risk_scorer import RiskScorer


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
    sessions         = load_spedia_sessions(
        "spedia_anomaly_detection/data/SPEDIA_preprocessed.csv")
    pop_matrix       = load_population_matrix(
        "spedia_anomaly_detection/data/ctmc_transition_matrix.csv")

    user_sessions = defaultdict(list)
    for s in sessions:
        user_sessions[s["user_id"]].append(s)

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

    extractor = StateExtractor()
    ctmc      = CTMCScorer()
    rules     = RuleEngine()
    scorer    = RiskScorer()

    print("\n=== FALSE POSITIVES (normal sessions that fired alerts) ===")
    print(f"{'User':<20} {'Score':>6} {'CTMC':>6} {'Rules':>6} "
          f"{'States':>6} {'Rules fired'}")
    print("-" * 80)

    fp_users = Counter()

    for session in test_sessions:
        if session.get("anomaly") != 0:
            continue

        user   = session["user_id"]
        states = extractor.extract_states(session)
        if not states:
            continue

        matrix = user_matrices.get(user, pop_matrix)
        n_train = user_counts.get(user, 0)

        ctmc_score = ctmc.score(states, matrix, n_train)
        violations = rules.check_all_rules(states, session["events"], user)
        result     = scorer.compute(
            user_id=user, session_id=session["session_id"],
            ctmc_score=ctmc_score, violations=violations,
            total_sessions=n_train,
        )

        if result.risk_score >= 5.0:
            fp_users[user] += 1
            rule_names = [v.rule_id for v in violations]
            print(f"{user:<20} {result.risk_score:>6.1f} "
                  f"{result.ctmc_score:>6.1f} {result.rule_score:>6.1f} "
                  f"{len(states):>6} {rule_names}")

    print(f"\n=== FALSE POSITIVE COUNT BY USER ===")
    for user, count in fp_users.most_common():
        print(f"  {user:<25} {count} false alarms")

    print(f"\n=== MISSED THREATS (anomalous sessions that scored below 5) ===")
    print(f"{'User':<20} {'Score':>6} {'CTMC':>6} {'Rules':>6} "
          f"{'States':>6} {'Top states'}")
    print("-" * 80)

    fn_users = Counter()

    for session in test_sessions:
        if session.get("anomaly") != 1:
            continue

        user   = session["user_id"]
        states = extractor.extract_states(session)
        if not states:
            continue

        matrix  = user_matrices.get(user, pop_matrix)
        n_train = user_counts.get(user, 0)

        ctmc_score = ctmc.score(states, matrix, n_train)
        violations = rules.check_all_rules(states, session["events"], user)
        result     = scorer.compute(
            user_id=user, session_id=session["session_id"],
            ctmc_score=ctmc_score, violations=violations,
            total_sessions=n_train,
        )

        if result.risk_score < 5.0:
            fn_users[user] += 1
            top_states = Counter(states).most_common(3)
            top_str    = ", ".join(f"{s}:{c}" for s,c in top_states)
            print(f"{user:<20} {result.risk_score:>6.1f} "
                  f"{result.ctmc_score:>6.1f} {result.rule_score:>6.1f} "
                  f"{len(states):>6} {top_str}")

    print(f"\n=== MISSED THREAT COUNT BY USER ===")
    for user, count in fn_users.most_common():
        print(f"  {user:<25} {count} missed threats")


if __name__ == "__main__":
    main()
