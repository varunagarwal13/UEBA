# Isolation Forest Training Pipeline

*Pursuant to Phase 7 and 8 of the V2 Master Prompt.*

This document describes the reproducible machine learning pipeline designed to train the new Isolation Forest (IF) anomaly detector completely free of Target Leakage and Circular Learning.

## 1. Feature Ingestion & Sessionization
The training script loads `SPEDIA_preprocessed.csv` using the existing `load_spedia_sessions()` function, which perfectly structures the data around a robust 30-minute inactivity threshold. These raw sessions are transformed into a numerical design matrix `X` using the newly engineered `FeatureExtractor`.

## 2. Chronological Splitting (Phase 7)
To simulate real-world SOC environments, time-travel leakage must be strictly prevented. The dataset spanning March 6, 2025 to March 30, 2025 is partitioned **chronologically**, not randomly.

* **Training Set:** Start to March 20, 2025 (First ~15 days)
* **Validation Set:** March 21 to March 25, 2025 (Next ~5 days)
* **Test Set:** March 26 to End (Final ~5 days)

The IF model learns baseline norms exclusively on the Training configuration representing the past.

## 3. Training the Isolation Forest (Phase 8)
An Isolation Forest model from `scikit-learn` is trained entirely via **unsupervised learning**.
It observes only the 16 numerical features derived by `FeatureExtractor` in the Train split. It never sees `Anomaly`, nor any V1-derived rules (`Risk_Score`, `Rule_Count`, etc.).

**Hyperparameters:**
* `n_estimators`: 100
* `contamination`: Auto (adjusted dynamically, though typically ~5-10% of sessions are highly anomalous).
* `random_state`: 42 (ensures exact reproducibility across pipeline runs).

## 4. Inference & Scoring
For an unseen session in the Validation/Test set, the pipeline:
1. Extracts `X_test` via `FeatureExtractor`.
2. Computes the anomaly score using `model.decision_function(X_test)`.
3. Normalizes and flips the score into a `0-100` Human-Readable severity scale.

The resulting artifact is saved directly to disk (`analytics/models/if_model.pkl`) for real-time inference by the V2 risk scorer.
