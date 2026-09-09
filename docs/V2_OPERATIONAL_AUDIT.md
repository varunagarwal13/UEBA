# UEBA V2 OPERATIONAL AUDIT

## Components Status Report

| Component | Implementation Status | Runtime Status | Persistence Status | Test Status | Known Degradation | Exact File |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AnalyticsPipeline** | Implemented | Operational | N/A | Missing | None | `analytics/pipeline/analytics_pipeline.py` |
| **FastAPI Ingestion** | Implemented | Operational (`/logs/user`) | SQLite | Missing | Bypass on `/logs/network` | `backend/app/routers/logs.py` |
| **Sessionization** | Implemented | Operational | Transient | Missing | Drops non-temporal events | `analytics/data/spedia/loader.py` |
| **FeatureExtractor** | Implemented | Operational | Vectorized | Missing | None | `analytics/pipeline/feature_extractor.py` |
| **IF Training Code** | Implemented | Run Complete | Pickled Artifact | Missing | Lacking metric serialization | `analytics/train_isolation_forest.py` |
| **IF Inference Code** | Implemented | Operational | N/A | Missing | No feature order hash check | `analytics/models/isolation_forest/inference.py` |
| **CTMCManager** | Scaffolded | Degraded | Empty Matrix | Missing | `{}` is passed to `population_matrix` | `analytics/pipeline/ctmc_scorer.py` |
| **Personal Baseline** | Scaffolded | Partially Operational | Transient | Missing | Matrices lost on reboot | `analytics/pipeline/ctmc_scorer.py` |
| **RuleEngine** | Implemented | Operational | N/A | Missing | None | `analytics/pipeline/rule_engine.py` |
| **RiskScorer** | Implemented | Operational | N/A | Missing | Hardcoded fusion weights (20/25/40/15) | `analytics/pipeline/risk_scorer.py` |
| **Explainer** | Implemented | Operational | Appended to string | Missing | None | `analytics/pipeline/explainer.py` |
| **CRUD/DB Schema** | Implemented | Operational | SQLite (`app.db`) | Missing | Missing baseline tables | `backend/app/crud.py` |
| **PyTest Suite** | Not Implemented | Broken | N/A | 0 Passed, 1 Error | Event loop scope deprecation crash | `tests/` |

## Initial Execution Summary
The actual codebase executes beautifully from CSV -> Ingestion -> Feature Extraction -> IF Inference -> DB Push for `/logs/user`.
However, CTMC/Personal statistics exist strictly in-memory and default to degraded empty states, Risk weight limits are statically hardcoded without dynamic inference, and PyTest execution loops completely fail upon collection.

*Audit Generated: Phase 1*
