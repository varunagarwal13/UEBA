import os
import pandas as pd
import numpy as np
import urllib.request
import zipfile

# ---------------------------------------------------------
# CONSTANTS & CONFIGURATION
# ---------------------------------------------------------
DATA_DIR = "spedia_anomaly_detection/data"
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DATA_DIR, "MASTER_preprocessed.csv")

# NOTE: Direct download links for CERT and LANL often require authentication (Kaggle or CMU SEI).
# This script assumes you have either placed the raw CSVs in the raw_data folder OR 
# have authenticated download links available here.
URLS = {
    # Example placeholder URLs
    "CERT": "https://placeholder-link.com/cert_logon.csv", 
    "LANL": "https://placeholder-link.com/lanl_auth.csv",
    "BETH": "https://placeholder-link.com/beth_dataset.csv"
}

# ---------------------------------------------------------
# 1. DOWNLOAD LOGIC (Placeholder for Kaggle/Direct links)
# ---------------------------------------------------------
def download_dataset(name, url, dest_folder):
    """Downloads a dataset if it doesn't already exist."""
    print(f"[*] Downloading {name} dataset...")
    os.makedirs(dest_folder, exist_ok=True)
    file_path = os.path.join(dest_folder, f"{name.lower()}_raw.csv")
    
    if os.path.exists(file_path):
        print(f"    - {name} dataset already exists at {file_path}")
        return file_path

    try:
        # In Colab, you might use !kaggle datasets download -d <dataset> instead
        print(f"    - Please manually upload {name.lower()}_raw.csv if url is a placeholder.")
        # urllib.request.urlretrieve(url, file_path) 
    except Exception as e:
        print(f"    [!] Error downloading {name}. Check authentication or URLs. ({e})")
        
    return file_path

# ---------------------------------------------------------
# 2. ETL TRANSFORMATION LOGIC
# ---------------------------------------------------------

def process_cert(file_path):
    """
    CERT datasets usually have headers: id, date, user, pc, activity.
    And a separate answers.csv identifying anomalous insiders.
    """
    print("[*] Processing CERT Dataset...")
    if not os.path.exists(file_path):
        return pd.DataFrame()
        
    df = pd.read_csv(file_path)
    
    # Map to Target Schema
    df = df.rename(columns={
        "user": "User",
        "date": "Timestamp",
        "activity": "Action" # e.g. Logon, Logoff
    })
    
    # CERT assigns 'Activity' based on the file type (e.g. logon.csv vs file.csv)
    # We assume this is the logon dataset for demonstration
    df["Activity"] = "Session" 
    
    # In CERT, ground truth is usually stored in an answers/insiders CSV.
    # Below is a stand-in for the merge operation:
    # truth_df = pd.read_csv("answers.csv")
    # df['Anomaly'] = df['User'].apply(lambda x: 1 if x in truth_df['user'].values else 0)
    df["Anomaly"] = 0 # Placeholder until answers.csv is merged (Set appropriately)
    
    return df[["User", "Timestamp", "Activity", "Action", "Anomaly"]]

def process_lanl(file_path):
    """
    LANL headers (auth.txt): time, source_user, dest_user, source_comp, dest_comp, auth_type, log_type, auth_orient, success
    """
    print("[*] Processing LANL Dataset...")
    if not os.path.exists(file_path):
        return pd.DataFrame()
        
    # LANL often comes without headers, so we define them:
    cols = ["time", "source_user", "dest_user", "source_comp", "dest_comp", "auth_type", "log_type", "auth_orient", "success"]
    df = pd.read_csv(file_path, names=cols)
    
    # Convert LANL epoch time to Datetime (LANL time is seconds relative to day 1)
    # Assuming Day 1 is arbitrarily 2024-01-01 for timestamp consistency
    df["Timestamp"] = pd.to_datetime('2024-01-01') + pd.to_timedelta(df['time'], unit='s')
    
    df = df.rename(columns={
        "source_user": "User",
        "log_type": "Activity",
        "auth_type": "Action"
    })
    
    # LANL anomalies are provided in redteam.csv
    # redteam_df = pd.read_csv("redteam.csv")
    # merge logic based on user and time window
    df["Anomaly"] = np.where(df["User"].str.startswith("U"), 0, 1) # Example heuristic logic
    
    return df[["User", "Timestamp", "Activity", "Action", "Anomaly"]]

def process_beth(file_path):
    """
    BETH headers: timestamp, host_id, processId, processName, syscall, sus, evil
    """
    print("[*] Processing BETH Dataset...")
    if not os.path.exists(file_path):
        return pd.DataFrame()
        
    df = pd.read_csv(file_path)
    
    df = df.rename(columns={
        "host_id": "User",        # Translating Host to User equivalent for behavioral engine
        "timestamp": "Timestamp",
        "processName": "Activity",
        "syscall": "Action"
    })
    
    # BETH explicit labeling:
    # Label is 1 if marked as 'evil' or 'sus' (suspicious)
    df["Anomaly"] = np.where((df["evil"] == 1) | (df["sus"] == 1), 1, 0)
    
    # Convert BETH unix epoch timestamp
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], unit='s')
    
    return df[["User", "Timestamp", "Activity", "Action", "Anomaly"]]

# ---------------------------------------------------------
# 3. SCHEMA VERIFICATION & FUSION
# ---------------------------------------------------------
def verify_schema(df, source_name):
    """Ensures dataframe perfectly matches UEBA V2 target pipeline."""
    expected_cols = ["User", "Timestamp", "Activity", "Action", "Anomaly"]
    
    for col in expected_cols:
        if col not in df.columns:
            raise ValueError(f"Schema mismatch in {source_name}: Missing column '{col}'")
            
    # Verify labels (can only be 0 or 1)
    unique_labels = df["Anomaly"].unique()
    for lbl in unique_labels:
        if lbl not in [0, 1]:
            raise ValueError(f"Label mismatch in {source_name}: Anomaly column must be strictly [0, 1]. Found: {unique_labels}")
            
    print(f"    [+] {source_name} Schema & Labels verified. ({len(df)} events)")

def main():
    print("=== UEBA Dataset Fusion Pipeline ===\n")
    
    raw_dir = os.path.join(DATA_DIR, "raw_sources")
    cert_path = download_dataset("CERT", URLS["CERT"], raw_dir)
    lanl_path = download_dataset("LANL", URLS["LANL"], raw_dir)
    beth_path = download_dataset("BETH", URLS["BETH"], raw_dir)
    
    # ETL DataFrames
    df_cert = process_cert(cert_path)
    df_lanl = process_lanl(lanl_path)
    df_beth = process_beth(beth_path)
    
    datasets = []
    if not df_cert.empty:
        verify_schema(df_cert, "CERT")
        datasets.append(df_cert)
    if not df_lanl.empty:
        verify_schema(df_lanl, "LANL")
        datasets.append(df_lanl)
    if not df_beth.empty:
        verify_schema(df_beth, "BETH")
        datasets.append(df_beth)
        
    if not datasets:
        print("\n[!] No datasets processed. Please supply the raw CSVs in the data/raw_sources directory in Colab.")
        return
        
    # Concatenate all datasets
    print("\n[*] Fusing datasets...")
    master_df = pd.concat(datasets, ignore_index=True)
    
    # CRITICAL: Sort chronologically as per UEBA V2 Reproducibility Contract
    print("[*] Sorting chronologically...")
    master_df["Timestamp"] = pd.to_datetime(master_df["Timestamp"], format='mixed', utc=True)
    master_df = master_df.sort_values(by="Timestamp").reset_index(drop=True)
    
    # Output
    master_df.to_csv(OUTPUT_FILE, index=False)
    
    # Final Summary
    anomaly_rate = (master_df['Anomaly'].sum() / len(master_df)) * 100
    print(f"\n=== FUSION COMPLETE ===")
    print(f"Total Unified Events:  {len(master_df)}")
    print(f"Total Anomalous:       {master_df['Anomaly'].sum()} ({anomaly_rate:.2f}%)")
    print(f"Saved to:              {OUTPUT_FILE}")
    print("\nYou can now update `train_isolation_forest.py` chronological bound dates to train against this file!")

if __name__ == "__main__":
    main()
