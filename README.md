# SaaS UEBA — CTMC-centered insider threat detection (MVP)

Confidence-weighted insider-threat detection pipeline, validated on
the SPEDIA dataset. Four detection engines (rule-based, ECOD,
HDBSCAN, CTMC) feed a fused risk score via inverse-variance weighting.

## Quickstart (GitHub Codespaces)
1. Click **Code -> Codespaces -> Create codespace on main**. The
   devcontainer installs everything in `requirements.txt` automatically.
2. Download the SPEDIA dataset and drop the CSV into `data/raw/`
   (gitignored — never commit it):
   `https://zenodo.org/records/15495572/files/logs_SPEDIA.csv?download=1`
3. Run `python -m pytest tests/` — should pass with 2 green tests
   (fusion math sanity checks) even before any engine is implemented.
4. Open `notebooks/01_eda.ipynb` to start exploring the data.

## Repo layout
```
src/
  common/        canonical Event + EngineOutput contracts, DetectionEngine ABC
  ingest/        SPEDIA CSV -> canonical Event schema
  profile/       per-user temporal/access profile, entity graph
  detection/     rules.py, ecod.py, hdbscan_engine.py, ctmc.py — one file per engine
  fusion/        inverse-variance confidence-weighted fusion (implemented)
  eval/          PR-AUC, precision/recall, time-to-detect against SPEDIA labels
tests/           pytest — includes a hand-verified fusion math sanity test
notebooks/       EDA and scratch work
data/raw/        SPEDIA CSV goes here (gitignored)
data/processed/  normalized event tables (gitignored)
```

## Build order
1. Schema normalization (`src/ingest/`) — SPEDIA's 25 columns into
   the canonical `Event` tuple.
2. Profile layer (`src/profile/`) — per-user temporal/access profile.
3. Rule engine + ECOD — cheapest engines, get a baseline fast.
4. HDBSCAN.
5. CTMC — hardest engine, budget the most time.
6. Calibration — map each engine's raw score onto a comparable 0-100
   scale before fusion means anything.
7. Eval harness (`src/eval/`) — PR-AUC, precision/recall vs. SPEDIA labels.

See `CONTRIBUTING.md` for branch ownership and the interface contract
every engine must follow.

## Dataset
SPEDIA: 30-day MITRE ATT&CK-mapped insider-threat exercise, blending
real attacker behavior, role-based simulated activity, and synthetic
CERT-derived events. License: CC-BY.
