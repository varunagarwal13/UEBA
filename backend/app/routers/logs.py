"""
routers/logs.py
---------------
Handles CSV file uploads.
Uses pandas to parse the CSV, maps columns to DB model fields,
then bulk-inserts into SQLite.

Why pandas for ingestion? CSVs can have messy data — pandas handles
NaN values, mixed types, and date parsing cleanly.
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, models
import pandas as pd
import io
from datetime import datetime

router = APIRouter(prefix="/logs", tags=["Log Ingestion"])


# ── Map event_type strings to CTMC states ─────────────────────────────────────
CTMC_MAP = {
    "LOGIN":           "Login",
    "LOGOFF":          "Logout",
    "LOGOUT":          "Logout",
    "LOGIN_FAILED":    "Login_Failed",
    "EMAIL":           "Email",
    "HTTP":            "Browser",
    "FILE_ACCESS":     "File_Access",
    "FILE_MODIFY":     "File_Modify",
    "FILE_DELETE":     "File_Delete",
    "FILE_ADD":        "File_Add",
    "COMMAND":         "Command",
    "SUSPICIOUS_CMD":  "Suspicious_Command",
    "PRIVILEGE_CMD":   "Privilege_Command",
    "DEVICE":          "Device_Event",
}

def infer_event_type(activity: str, action: str = "") -> str:
    """
    Convert raw Activity + Action fields from SPEDIA CSV
    into a clean event_type string.
    """
    act = str(activity).strip().lower()
    act_map = {
        "session": "LOGIN" if "fail" not in str(action).lower() else "LOGIN_FAILED",
        "email":   "EMAIL",
        "http":    "HTTP",
        "file":    "FILE_ACCESS",
        "command": "COMMAND",
        "device":  "DEVICE",
    }
    if act == "session" and "logoff" in str(action).lower():
        return "LOGOFF"
    if act == "file":
        a = str(action).lower()
        if "delet" in a: return "FILE_DELETE"
        if "modif" in a: return "FILE_MODIFY"
        if "add"   in a: return "FILE_ADD"
    return act_map.get(act, act.upper())


@router.post("/user", summary="Upload User Event Logs (CSV)")
async def upload_user_logs(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts a CSV file of user events.
    Expected columns (flexible — maps what's available):
      User, Timestamp, Activity, Action, CTMC_State,
      Risk_Score, Rule_Count, Rules_Triggered, Anomaly, Description
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files accepted.")

    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content), low_memory=False)
    except Exception as e:
        raise HTTPException(400, f"Could not parse CSV: {e}")

    # Normalize column names — strip spaces, lowercase for matching
    df.columns = df.columns.str.strip()

    # Identify user column
    user_col = next((c for c in df.columns if c.lower() in ["user","user_id","userid"]), None)
    if not user_col:
        raise HTTPException(400, "CSV must have a 'User' or 'user_id' column.")

    # Ensure all users exist in the users table
    for user_id in df[user_col].dropna().unique():
        crud.get_or_create_user(db, str(user_id))

    # Parse timestamps
    ts_col = next((c for c in df.columns if "timestamp" in c.lower() or "time" in c.lower()), None)
    if ts_col:
        df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")

    # Build records list for bulk insert
    records = []
    for _, row in df.iterrows():
        user_id  = str(row.get(user_col, "UNKNOWN"))
        activity = str(row.get("Activity", row.get("activity", "")))
        action   = str(row.get("Action",   row.get("action",   "")))

        event_type = row.get("event_type", infer_event_type(activity, action))
        ctmc_state = row.get("CTMC_State", CTMC_MAP.get(str(event_type).upper(), "Unknown"))

        ts = row.get(ts_col) if ts_col else None
        ts = ts if pd.notna(ts) else None
        hour = ts.hour if ts else None
        dow  = ts.dayofweek if ts else None

        records.append({
            "user_id":        user_id,
            "timestamp":      ts,
            "event_type":     str(event_type),
            "ctmc_state":     str(ctmc_state),
            "activity":       activity,
            "action":         action,
            "description":    str(row.get("Description", "")),
            "risk_score":     float(row.get("Risk_Score",  row.get("risk_score",  0.0)) or 0.0),
            "rule_count":     int(  row.get("Rule_Count",  row.get("rule_count",  0))   or 0),
            "rules_triggered":str(row.get("Rules_Triggered", row.get("rules_triggered", "")) or ""),
            "is_anomaly":     bool( row.get("Anomaly",     row.get("is_anomaly", False))),
            "hour":           hour,
            "day_of_week":    dow,
            "is_after_hours": bool(hour is not None and (hour < 7 or hour > 20)),
            "is_weekend":     bool(dow  is not None and dow >= 5),
        })

    crud.bulk_insert_events(db, records)

    return {
        "status":        "success",
        "rows_inserted": len(records),
        "filename":      file.filename,
    }


@router.post("/network", summary="Upload Network Event Logs (CSV)")
async def upload_network_logs(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts network logs CSV.
    Expected columns: src_ip, dst_ip, bytes, timestamp, protocol, event_type
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files accepted.")

    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content), low_memory=False)
    except Exception as e:
        raise HTTPException(400, f"Could not parse CSV: {e}")

    df.columns = df.columns.str.strip()

    ts_col = next((c for c in df.columns if "time" in c.lower()), None)
    if ts_col:
        df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")

    records = []
    for _, row in df.iterrows():
        ts = row.get(ts_col) if ts_col else None
        records.append({
            "user_id":    str(row.get("user_id", row.get("User", ""))) or None,
            "timestamp":  ts if (ts and pd.notna(ts)) else None,
            "src_ip":     str(row.get("src_ip",  "")),
            "dst_ip":     str(row.get("dst_ip",  "")),
            "bytes_sent": int(row.get("bytes",   row.get("bytes_sent", 0)) or 0),
            "protocol":   str(row.get("protocol","UNKNOWN")),
            "event_type": str(row.get("event_type", "NETWORK")),
            "is_anomaly": bool(row.get("Anomaly", row.get("is_anomaly", False))),
        })

    crud.bulk_insert_network_events(db, records)

    return {
        "status":        "success",
        "rows_inserted": len(records),
    }