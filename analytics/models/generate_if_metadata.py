import os
import json
import hashlib
import pickle
import sklearn
import sys
from datetime import datetime

def generate():
    print("Generating Model Artifact Integrity Hashes...")
    model_path = "analytics/models/if_model.pkl"
    schema_path = "analytics/models/if_feature_schema.json"

    if not os.path.exists(model_path):
        print(f"Error: {model_path} missing.")
        return

    with open(model_path, "rb") as f:
        data = f.read()
        model_hash = hashlib.sha256(data).hexdigest()

    with open(schema_path, "rb") as f:
        schema_data = f.read()
        schema_hash = hashlib.sha256(schema_data).hexdigest()

    metadata = {
        "model_sha256": model_hash,
        "feature_schema_sha256": schema_hash,
        "training_dataset_identifier": "SPEDIA_preprocessed.csv (2025-03-06 to 2025-03-20)",
        "training_date": datetime.utcnow().isoformat() + "Z",
        "sklearn_version": sklearn.__version__,
        "python_version": sys.version.split(" ")[0],
        "hyperparameters": {
            "n_estimators": 100,
            "contamination": "auto",
            "random_state": 42
        }
    }

    out_path = "analytics/models/if_model_metadata.json"
    with open(out_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Locked artifact to: {model_hash}")

if __name__ == "__main__":
    generate()
