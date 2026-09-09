# UEBA V1 Codebase Audit & V2 Plan

*Audit conducted pursuant to Phase 0 of the V2 Master Prompt.*

## 1. Current Architecture & Data Flow
The V1 system is built around a linear pipeline encapsulated in `analytics/pipeline/analytics_pipeline.py`. 

The current flow is:
1. `StateExtractor` derives CTMC states from raw session events.
2. `CTMCScorer` evaluates the state sequence probability (incorporating specific state bonuses).
3. `RuleEngine` checks against hardcoded policies.
4. `RiskScorer` fuses CTMC (60%) and Rule scores (40%) to output a final 0-100 risk score and determining severity (Low/Medium/High/Critical).
5. `Explainer` translates this composite risk into human-readable SOC narratives.
6. The resulting object is passed to FastAPI endpoints as seen in the isolated backend integration.

## 2. Existing Machine Learning (CTMC)
- Logic resides in `analytics/ctmc/ctmc_scorer.py`.
- Evaluates the total sequence probability using `math.log` of sequential node transitions.
- Scores are pulled upward with a static `scaling_factor=2.0`. 
- High-risk states (`Suspicious_Command`, etc.) add arbitrary bonus risk thresholds.
- Includes a "Trust Dampener" which decreases false positives for users with limited profiles (under 10 sessions recorded).

## 3. Existing Rule Engine & Risk Scoring
- **Rules (`analytic/rule_engine/rule_engine.py`)**: Defines 13 rules specifically modeled on insider threat / external compromise activity (After-hours login, Bulk File Access, Exfiltration indicators like Priv Escalation -> Data Access). 
- **Risk Fusion (`analytics/risk_scoring/risk_scorer.py`)**: 
  - Weight calculation is static: `CTMC * 0.60 + RULES * 0.40`.
  - Also incorporates an "Agreement Boost" if both systems identify risk over 40.
  - Generates confidence penalties for single-system flags to suppress false positives.
  - Exposes an `if_score` variable for an Isolation Forest, which currently always returns `0.0` (unimplemented).

## 4. Current Gaps vs V2 Target Architecture
1. **Model Gaps**: The Isolation Forest anomaly detector is scaffolded but not implemented.
2. **Feature Extraction**: Features are derived repeatedly across rules rather than from a central numerical `feature_extractor` which is required for an Isolation Forest.
3. **Baselining Gaps**: Baseline comparisons (Personal vs Population) simply pass either a population matrix or personal matrix to CTMC. There are no structured Peer-Group baselines.
4. **Integration Gaps**: The backend FastAPI doesn't actually trigger the ML layer during ingestion.

## 5. V2 Technical Readiness and Compatibility Risks
The codebase is extremely clean, heavily structured around decoupling ML logic, scaling limits, and deterministic execution. It utilizes classes strictly, guaranteeing safe testing boundaries. 
- *Compatibility Risk*: Modifying the single sequence `StateExtractor` logic could disrupt V1 scoring thresholds since `scaling_factor=2.0` relies on current probabilistic density. The target Risk Fusion module must remain loosely decoupled to maintain V1 behaviors natively while introducing new capabilities (like Network UEBA and Trend Analysis).
