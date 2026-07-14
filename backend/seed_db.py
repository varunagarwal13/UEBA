"""
seed_db.py
----------
Run this ONCE after Person 1 gives you the preprocessed CSV.
It loads all the data directly into SQLite without going through the API.

Usage:
    python seed_db.py --file data/SPEDIA_preprocessed.csv
"""

import argparse
import pandas as pd
from app.database import SessionLocal, engine, Base
from app import models, crud

Base.metadata.create_all(bind=engine)

def seed(filepath: str):
    db = SessionLocal()
    print(f"[INFO] Loading {filepath}...")
    df = pd.read_csv(filepath, low_memory=False)
    print(f"[OK]   {len(df):,} rows loaded")

    # Parse timestamp
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")

    # Create users
    user_col = "User" if "User" in df.columns else "user_id"
    for uid in df[user_col].dropna().unique():
        crud.get_or_create_user(db, str(uid))
    print(f"[OK]   {df[user_col].nunique()} users created")

    # Build event records
    records = []
    for _, row in df.iterrows():
        ts = row.get("Timestamp")
        ts = ts if pd.notna(ts) else None
        hour = ts.hour if ts else None
        dow  = ts.dayofweek if ts else None

        records.append({
            "user_id":         str(row.get(user_col, "UNKNOWN")),
            "timestamp":       ts,
            "event_type":      str(row.get("event_type",  row.get("Activity", "UNKNOWN"))).upper(),
            "ctmc_state":      str(row.get("CTMC_State",  "Unknown")),
            "activity":        str(row.get("Activity",    "")),
            "action":          str(row.get("Action",      "")),
            "description":     str(row.get("Description", "")),
            "risk_score":      float(row.get("Risk_Score", 0.0) or 0.0),
            "rule_count":      int(  row.get("Rule_Count", 0)   or 0),
            "rules_triggered": str(row.get("Rules_Triggered", "") or ""),
            "is_anomaly":      bool( row.get("Anomaly", False)),
            "hour":            hour,
            "day_of_week":     dow,
            "is_after_hours":  bool(hour is not None and (hour < 7 or hour > 20)),
            "is_weekend":      bool(dow  is not None and dow >= 5),
        })

    # Bulk insert in chunks to avoid memory issues
    CHUNK = 5000
    for i in range(0, len(records), CHUNK):
        crud.bulk_insert_events(db, records[i:i+CHUNK])
        print(f"  Inserted rows {i}–{min(i+CHUNK, len(records))}")

    print(f"[OK]   All {len(records):,} events inserted into DB")
    db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="data/SPEDIA_preprocessed.csv")
    args = parser.parse_args()
    seed(args.file)