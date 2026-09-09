from typing import Dict, List, Any
import numpy as np

class PersonalBaselineManager:
    """
    Stateful rolling baseline engine.
    Calculates behavioral standard deviations for a user WITHOUT future-data leakage.
    For a given session, it calculates the Z-Score deviation against past sessions,
    THEN incorporates the current session into the state history.
    """
    
    def __init__(self):
        # Maps user_id -> List of historical numerical feature vectors
        self.user_history: Dict[str, List[np.ndarray]] = {}
        # Minimum sessions required before a baseline is considered established
        self.min_history = 5
        
    def score_and_update(self, user_id: str, new_features: Dict[str, float]) -> float:
        """
        Receives a dictionary of clean session features (from FeatureExtractor).
        Returns a 0-100 anomaly deviation score. Follows strict temporal ordering.
        """
        vector = np.array(list(new_features.values()))
        history = self.user_history.get(user_id, [])
        
        score = 0.0
        
        if len(history) >= self.min_history:
            matrix = np.vstack(history)
            
            # Add a small epsilon to variance to prevent divide-by-zero on constants
            means = np.mean(matrix, axis=0)
            stds  = np.std(matrix, axis=0) + 1e-6
            
            # Compute bounded absolute Z-scores
            z_scores = np.abs(vector - means) / stds
            
            # The baseline deviation score is the average Z-score across dimensions, capped
            avg_z = np.mean(z_scores)
            
            # Normalize: a Z-score of 3.0 represents extreme deviation (100)
            # Z-score of 0.0 is perfect normality (0)
            raw_score = (avg_z / 3.0) * 100.0
            score = max(0.0, min(100.0, float(raw_score)))
            
        # Explicit chronological update (must happen AFTER scoring)
        if user_id not in self.user_history:
            self.user_history[user_id] = []
            
        # Keep maximum history to prevent unbounded memory growth and favor recent context
        self.user_history[user_id].append(vector)
        if len(self.user_history[user_id]) > 50:
            self.user_history[user_id].pop(0)
            
        return score
