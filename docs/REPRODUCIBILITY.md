# UEBA V2 REPRODUCIBILITY CONTRACT
**Status: Locked & Verified**

## Mathematical Determinism Constraints
To achieve mathematically identical model output across independent training runs, the following constraints strictly apply:

| Parameter | Bound Constraint |
|:---|:---|
| **Random Seed (`random_state`)** | 42 |
| **`n_estimators`**               | 100 |
| **`contamination`**              | "auto" |
| **Validation Tuning Selection**  | `np.linspace(50, 99, 50)`, F1 Maximization |
| **Chosen Sub-threshold**         | `-0.1464` |

---

## Dataset Chronology Constraints (Phase 13 Proof)
Random shuffling is functionally catastrophic for behavioral analysis. Training must unconditionally observe strict chronology:

- **Source:** `spedia_anomaly_detection/data/SPEDIA_preprocessed.csv`
- **Training Interval:** 2025-03-06 through 2025-03-20
- **Validation Interval:** 2025-03-21 through 2025-03-25
- **Testing Interval:** 2025-03-26 through 2025-03-30
- **Target Leakage (`Anomaly`) State:** Explicitly removed via `feature_extractor.py`.

## Physical Serial Artifacts
- **Model Pickle Hash (`if_model.pkl`):** `dcdd47eb7c54b1a34816c38695aad7fee6ec24c77edbf00ced36ed859676eff8`
- **Scikit-Learn Verified Version:** `1.2.2`
- **Python Execution:** 3.11.x

**Pipeline Verification Standard:** 
Any alteration to the dataset path, bounding interval limits, or `extractor.feature_names` array index order identically forces a metadata hash failure to trigger during load, blocking corruption.
