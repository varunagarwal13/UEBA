# V2.1 PRE-IMPLEMENTATION AUDIT

## Component State Assessment

| Component | Existing V2 State | V2.1 Modification | Risk |
| :--- | :--- | :--- | :--- |
| **Database Schema** | `User`, `Event`, `NetworkEvent`, `Alert`, `RiskProfile`, `PersonalBaseline` present. | Extend `PersonalBaseline` schema to `PersonalBehaviorProfile` (or upgrade in place). Add `AttackChain`, `InvestigationCase`, `CaseAlert`. | Moderate Schema Conflict |
| **API Endpoints** | `/logs/*`, `/risk`, `/dashboard`, `/alerts` operational. | Need extended endpoints for `/user/{u}/profile`, `/cases`, `/attack-chain`. | Low |
| **Behavioral profile** | `PersonalBaselineManager` uses simple generic multi-dimensional matrix comparisons. | Requires statistical metric splitting (`count`, `mean`, `variance`) rather than arbitrary distance scores, partitioned by `NEW`/`LEARNING`/`ESTABLISHED` maturity bounds. | High Computational Overhead |
| **Attack chain** | Completely Absent. | Generate mapped continuum bounds linked via timeline logic to aggregate chains across varying sessions chronologically. | High Temporal Leakage |
| **Explainability** | Concatenates active tools bounding alert outputs. | Dynamic translation describing deviations ("5.2x baseline burst") rather than arbitrary severity words. | Moderate Dependency Integrity |
| **Cases** | Absent. | Group linked alerts mechanically. | Low |
| **Ablation Assessment** | Offline scripts (`Evaluate_v1_vs_if.py`) | Generate `ablation.py` structurally executing every sub-combination of internal components against formal Test bounds. | Moderate |

## Forensic Contract Verification
- **Isolation Forest Integrity:** Passed (`if_model_metadata.json` verifies cryptographic hashes during initialization).
- **Leakage Integrity:** Passed (labels physically separated in loaders).
- **Chronological Split Integrity:** Passed (3 distinct time windows mapped natively).

## Development Rules of Engagement (ROE)
1. **Never fabricate missing datasets (e.g. peer groups).**
2. **Never train any baseline threshold using TEST sets.**
3. **Never allow time-travel causality (T+1 driving T alerts).**
4. **All features MUST have Pytest verification coverage before merging.**
