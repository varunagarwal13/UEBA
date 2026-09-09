# Feature Leakage Audit

*Pursuant to Phase 6 of the V2 Master Prompt.*

Before extracting numerical session features for the unsupervised Isolation Forest (or any future ML models), each prospective feature has been audited against the RAW DATA in `SPEDIA_preprocessed.csv`.

**CRITICAL PRINCIPLE:** The Isolation Forest must learn purely unsupervised behavior. It must not be fed pre-computed risk metrics or labels from V1.

| Feature (Session-Level) | Available at detection? | Leakage risk | Decision | Justification |
| ----------------------- | ----------------------- | ------------ | -------- | ------------- |
| `session_duration` | Yes | None | **SAFE** | Derived directly from `Timestamp` boundaries. |
| `event_count` | Yes | None | **SAFE** | Simple aggregation of raw data. |
| `hour_of_day` | Yes | None | **SAFE** | First event timestamp extraction. |
| `is_after_hours` | Yes | None | **SAFE** | Explicitly available in base metadata. |
| `is_weekend` | Yes | None | **SAFE** | Explicitly available in base metadata. |
| `login_count` | Yes | None | **SAFE** | Derived from `CTMC_State == Login`. |
| `failed_login_count`| Yes| None | **SAFE** | Derived from `CTMC_State == Login_Failed`. |
| `command_count` | Yes | None | **SAFE** | Derived from `CTMC_State` basic command types. |
| `suspicious_command_count` | Yes | Low | **SAFE** | Represents the native `Level` parsing from the security tool (Wazuh). It is an upstream telemetry flag, not V1 model output. |
| `file_access_count` | Yes | None | **SAFE** | Aggregated from `Action` fields. |
| `unique_files` | Yes | None | **SAFE** | Deduplication of `Path`/`Filename`. |
| `email_count` | Yes | None | **SAFE** | Derived from `Activity`. |
| `attachment_count` | Yes | None | **SAFE** | Extracted from `Attachments` column. |
| `bytes_transferred` | Yes | None | **SAFE** | Aggregated from `Size` tracking. |
| `unique_state_count`| Yes | None | **SAFE** | Count of unique `CTMC_State` representations. |
| `Risk_Score` | No (V1 logic) | **SEVERE** | **REJECTED** | V1 output. Direct target leakage risk. |
| `Risk_Label` | No (V1 logic) | **SEVERE** | **REJECTED** | V1 output. Cannot be used for unsupervised IF. |
| `Rule_Count` | No (V1 logic) | **SEVERE** | **REJECTED** | V1 output. |
| `Rules_Triggered` | No (V1 logic) | **SEVERE** | **REJECTED** | V1 output. |
| `Anomaly` | After-the-fact | **ABSOLUTE**| **REJECTED** | Target Ground Truth label. Must only be used in final evaluation metrics. |

All features marked **SAFE** will be implemented within a new `analytics/pipeline/feature_extractor.py` module to produce a clean, mathematical design matrix (X) for training.
