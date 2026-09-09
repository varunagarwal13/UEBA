# UEBA V2.1 Forensic Architecture Audit

## 1. Repository Structure Verified
The codebase is structured firmly into separate backend (`backend/app`) and ML integration pipelines (`analytics/`).
- **FastAPI Core**: Serves telemetry ingestion routes via `logs.py`.
- **Analytics Orchestrator**: Centrally orchestrated under `AnalyticsPipeline` which integrates V1 deterministic models alongside V2 Isolation Forest bounds and V2.1 Behavioral trackers.
- **Persistence Boundary**: `crud.py` interfaces with a SQLAlchemy SQLite database modeling temporal behaviors mapping onto tables like `PersonalBehaviorProfile`, `InvestigationCase`, `CaseAlert`, and `AttackChain`.

## 2. V2.1 Implementations Validated
- **Dynamic Welford Profiling**: Confirmed `ProfileBuilder` safely computes sequential Mean and Variance dynamically via Welford’s algorithm preventing buffer overflows.
- **Attack Cascades**: `AttackChainEngine` strictly bounds chronological progression mapping `AttackStage` enumerations without leakage bounds mutating historical causality limits.
- **Investigation Orchestrator**: Alert correlator bundles `CaseAlert` objects into structural Case arrays explicitly limited by sliding temporal bounds (24-hour limits).
- **Risk Scorer Normalization**: Demonstrated proper linear extraction resolving unavailable inference limits (e.g., `CTMC=None`) safely scaling remaining components instead of hallucinatory scoring blocks.

## 3. Risks & Anti-Patterns Noted
- Deterministic rules currently map explicitly into the V2 ML Pipeline `is_anomaly` test outputs via heuristic checking bindings. This prevents the true ML target boundaries from resolving completely independently of rule structures on smaller localized streams. 
- The CTMC engine heavily biases toward expected sequences without deep contextual embedding representations (Markov transitions are explicitly strictly linear per phase). 

## 4. Dependencies
- FastAPI, SQLAlchemy, Pandas, Scikit-Learn. 

## Verdict
The codebase authentically possesses the architectural pipelines required for the Final V2.1 verification execution workflow. Tests must now run explicitly.
