# SPEDIA Dataset Audit for UEBA V2

*Audit conducted pursuant to Phase 0 of the V2 Master Prompt.*

## 1. Dataset Inventory

The raw and preprocessed data is located within `spedia_anomaly_detection/data/`:
* `logs_SPEDIA_v2.csv` (Primary engineered logs - 36MB)
* `SPEDIA_preprocessed.csv` (Baseline preprocessed logs - 55MB)
* `ctmc_session_sequences.csv`
* `ctmc_transition_counts.csv`
* `ctmc_transition_matrix.csv`

## 2. Dataset Dimensions & Coverage

**Dimensions:** 72,250 rows.
**Temporal Coverage:** March 6, 2025 to March 30, 2025 (~24 days of log data).
**User Coverage:** 17 unique user identifiers. This implies dense behavioral generation averaging ~4,250 events per user.
**Anomalies:** 41,541 rows are flagged with `Anomaly=1`.

## 3. Schema & Event Coverage

Key features extracted from the primary dataframe:
* **Identifiers:** `id`, `Agent_name`, `User`, `Decoder_name`
* **Chronology:** `Timestamp`, `Hour`, `DayOfWeek`, `IsWeekend`, `IsAfterHours`
* **Log Properties:** `Full_log`, `Description`, `Level`, `Activity`, `Action`
* **Entity Operations:** `Filename`, `Path`, `Command`, `Attachments`, `Size`, `Size_before`, `Size_after`
* **Network / Comm. Fields:** `Url`, `To`, `Cc`, `Bcc`, `From`
* **Target / Rules (Pre-calculated):** `Anomaly`, `Risk_Score`, `Risk_Label`, `CTMC_State`, `Rules_Triggered`, `Rule_Count`

## 4. Label Availability

**Labels Exist:** Yes. 
The dataset contains supervised ground-truth `Anomaly` binary labels (0 or 1), as well as a pre-computed `Risk_Label`. Thus, supervised metric evaluations (Precision, Recall, F1, PR-AUC) for Isolation Forest and V2 modules will be directly supported.

## 5. Duplicate & Missing Data Risks

* Missing Values: While base fields like `User` and `Timestamp` are dense (~70k+), specialized fields like `Attachments`, `Cc`, and `Url` are understandably sparse depending on the `Activity` type.
* Leakage Risks: The dataset is pre-labeled with `Rules_Triggered` and `CTMC_State`. Care must be taken not to use standard rule outputs as input features to unsupervised models without proper ablation, preventing target leakage. Training evaluation must strictly use chronological splits (e.g. training on Days 1-15, testing on Days 16-24) to avoid time-travel leakage via dense usage metrics.

## 6. Model Suitability & V2 Impact

### Supported (Data Available)
* **Isolation Forest**: Session-based duration, feature counts, and behavior states are extremely well supported by the dense logging schemas.
* **Personal Baselines**: Calculating personal norms is suitable due to the extremely high event-per-user volume (approx 4,250).
* **Risk Trend & Attack Stage**: Time components are fine-grained and suitable for chronological trend extraction.
* **Exfiltration Detection**: Features like `Url`, `Attachments`, `Size`, `Path`, and `Email` usage directly support data staging/exfiltration heuristic detection.

### Unsupported / Severely Limited (Data Unavailable)
* **Peer Group Baseline**: There are **no** available role, department, or location columns to effectively group the 17 users. *Architectural Recommendation: Implement the interface but default it to disabled or map all users to a generic 'default_peer' group.*
* **Deep Network UEBA**: While basic application-layer strings (`Url`, emails) exist, low-level network packet telemetry (`src_ip`, `dst_ip`, `protocol`, `vpn_tunnels`) is entirely absent from the logs. *Architectural Recommendation: Evaluate network risk strictly using HTTP/Email fields rather than traditional netflow heuristics.*
