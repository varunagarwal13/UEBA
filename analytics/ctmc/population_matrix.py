# analytics/ctmc/population_matrix.py
#
# PURPOSE: Load SPEDIA's pre-computed population transition matrix.
#          Used as fallback for new users with no personal history.

import csv
from typing import Dict


def load_population_matrix(csv_path: str) -> Dict[str, Dict[str, float]]:
    matrix = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            from_state = row["From"]
            matrix[from_state] = {}
            for to_state, val in row.items():
                if to_state == "From":
                    continue
                try:
                    matrix[from_state][to_state] = float(val)
                except (ValueError, TypeError):
                    matrix[from_state][to_state] = 0.0
    return matrix


if __name__ == "__main__":
    m = load_population_matrix(
        "spedia_anomaly_detection/data/ctmc_transition_matrix.csv"
    )
    print(f"Loaded matrix: {len(m)} from-states")
    print("Sample — from Browser:")
    top = sorted(m.get("Browser", {}).items(), key=lambda x: x[1], reverse=True)[:3]
    for state, prob in top:
        print(f"  Browser -> {state}: {prob:.4f}")
