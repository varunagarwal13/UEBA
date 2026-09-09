import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import pickle
import numpy as np
import os

from analytics.state_extraction.state_extractor import StateExtractor
from analytics.ctmc.ctmc_scorer import CTMCScorer
from analytics.rule_engine.rule_engine import RuleEngine
from analytics.risk_scoring.risk_scorer import RiskScorer
from analytics.explainability.explainer import Explainer

# V2 Additions
from analytics.pipeline.feature_extractor import FeatureExtractor
from analytics.profiling.behavioral_profile import BehavioralProfileState
from analytics.profiling.profile_builder import ProfileBuilder
from analytics.profiling.profile_comparator import ProfileComparator
from analytics.risk_scoring.communication_scorer import CommunicationAnalytics
from analytics.risk_scoring.risk_trend import RiskTrendManager

# V2.1 Additions
from analytics.attack_chain.attack_stage import AttackStage
from analytics.attack_chain.stage_rules import StageMapper
from analytics.attack_chain.attack_chain_engine import AttackChainEngine, AttackChainState
from analytics.cases.case_engine import CaseEngine

ALERT_THRESHOLD    = 0.0
MIN_SESSION_LENGTH = 1

class AnalyticsPipeline:

    def __init__(self, population_matrix: Dict[str, Dict[str, float]]):
        self.population_matrix   = population_matrix
        self.user_matrices       = {}
        self.user_session_counts = {}
        
        # V1 engines
        self.state_extractor     = StateExtractor()
        self.ctmc_scorer         = CTMCScorer()
        self.rule_engine         = RuleEngine()
        self.explainer           = Explainer()
        
        # V2 engines
        # Locked V2 Fusion Weights based on empirical validation tuning:
        self.risk_scorer = RiskScorer(default_weights={"ctmc": 0.40, "rules": 0.25, "if": 0.20, "baseline": 0.15, "comm": 1.0, "trend": 1.0})
        
        self.feature_extractor = FeatureExtractor()
        
        # V2.1 Profiling Engines
        self.profile_builder = ProfileBuilder(anomaly_update_threshold_z=4.0)
        self.profile_comparator = ProfileComparator()
        self.user_profiles: Dict[str, BehavioralProfileState] = {}
        
        self.attack_chain_engine = AttackChainEngine(temporal_window_hours=24)
        self.user_chains: Dict[str, AttackChainState] = {}
        
        self.case_engine = CaseEngine(time_window_hours=24)
        self.open_cases: List[Dict] = []
        
        self.comm_analytics = CommunicationAnalytics()
        self.trend_manager = RiskTrendManager()
        
        # Phase 12: Cryptographically Verified Load
        self.if_model = None
        model_path = os.path.join(os.path.dirname(__file__), "..", "models", "if_model.pkl")
        metadata_path = os.path.join(os.path.dirname(__file__), "..", "models", "if_model_metadata.json")
        
        if os.path.exists(model_path) and os.path.exists(metadata_path):
            import json
            import hashlib
            with open(metadata_path, "r") as f:
                meta = json.load(f)
            expected_hash = meta.get("model_sha256")
            
            with open(model_path, "rb") as f:
                data = f.read()
                actual_hash = hashlib.sha256(data).hexdigest()
                
            if actual_hash == expected_hash:
                import pickle
                self.if_model = pickle.loads(data)
            else:
                print(f"SECURITY ALERT: Model artifact corruption detected! Expected {expected_hash}, got {actual_hash}")
                self.if_model = None

    def process_session(self, session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        user_id    = session.get("user_id", "unknown")
        session_id = session.get("session_id", "unknown")

        states = self.state_extractor.extract_states(session)
        if len(states) < MIN_SESSION_LENGTH:
            return None

        # V1 Base Inference
        matrix         = self.user_matrices.get(user_id, self.population_matrix)
        total_sessions = self.user_session_counts.get(user_id, 0)

        ctmc_score = self.ctmc_scorer.score(states, matrix, total_sessions)
        violations = self.rule_engine.check_all_rules(
            states, session.get("events", []), user_id=user_id
        )
        
        # V2 Independent ML Inferences
        features = self.feature_extractor.extract_features(session)
        
        # Validate IF Model integrity securely
        if_score = 0.0
        if self.if_model:
            x_vec = np.array(list(features.values())).reshape(1, -1)
            if_raw = -1.0 * self.if_model.decision_function(x_vec)[0]
            if_score = np.clip(100.0 * (if_raw - (-0.15)) / (0.15 - (-0.15)), 0, 100)
            
        # V2.1 Behavioral Profiling Integration
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = BehavioralProfileState(user_id=user_id)
            
        prof = self.user_profiles[user_id]
        
        # Compare current session first (to strictly prevent leakage from current logic into the baseline limit!)
        pb_score, dev_json = self.profile_comparator.compare(prof, features)
        
        # Only structurally update the behavior limit AFTER analyzing
        self.profile_builder.update_profile(prof, features, is_anomalous=(pb_score > 50), max_z_observed=dev_json["behavioral_deviation"].get("max_z_observed", 0.0))
        
        comm_res = self.comm_analytics.analyze_session(session)
        
        # V2.1 Attack Chain Engine
        rule_names = [v.rule_name for v in violations]
        stage = StageMapper.map_session(session, rule_names)
        
        active_chain = self.user_chains.get(user_id)
        # We need a proper timestamp for temporal bounds. Assuming chronologically ordered ingestion stream.
        session_time = datetime.utcnow() 
        active_chain = self.attack_chain_engine.process_event(active_chain, user_id, session_id, stage, session_time)
        self.user_chains[user_id] = active_chain
        
        attack_score = active_chain.risk_score
        
        # We compute a preliminary base risk to feed the momentum engine, then re-compute final with trend penalty
        base_result = self.risk_scorer.compute(
            user_id=user_id, session_id=session_id,
            ctmc_score=ctmc_score, violations=violations,
            total_sessions=total_sessions,
            if_score=if_score, personal_baseline_score=pb_score, attack_chain_score=attack_score, comm_score=comm_res.score, trend_score=0.0
        )
        
        trend = self.trend_manager.analyze_and_update(user_id, base_result.risk_score)
        
        final_result = self.risk_scorer.compute(
            user_id=user_id, session_id=session_id,
            ctmc_score=ctmc_score, violations=violations,
            total_sessions=total_sessions,
            if_score=if_score, personal_baseline_score=pb_score, attack_chain_score=attack_score, comm_score=comm_res.score, trend_score=trend.trend_score
        )

        if final_result.risk_score < ALERT_THRESHOLD:
            return None

        alert_id = f"ALT{str(uuid.uuid4())[:8].upper()}"
        
        # V2.1 Alert Correlation (Cases)
        # Map the solitary alert to macro-investigation cases
        case = self.case_engine.evaluate_alert(
            user_id=user_id, alert_id=alert_id,
            alert_score=final_result.risk_score, alert_stage=stage.value, alert_time=session_time, open_cases=self.open_cases
        )
        
        if case not in self.open_cases:
            self.open_cases.append(case)
            
        explanation = self.explainer.explain(
            alert_id       = alert_id,
            user_id        = user_id,
            state_sequence = states,
            violations     = violations,
            risk_score     = final_result.risk_score,
            severity       = final_result.severity,
            ctmc_score     = final_result.ctmc_score,
            rule_score     = final_result.rule_score,
            confidence     = final_result.confidence,
            if_score       = final_result.if_score,
            pb_score       = final_result.personal_baseline_score,
            attack_score   = final_result.attack_chain_score,
            dev_json       = dev_json,
            attack_stage   = stage.value
        )

        return {
            "alert": {
                "alert_id":       alert_id,
                "user_id":        user_id,
                "risk_score":     final_result.risk_score,
                "severity":       final_result.severity,
                "detection_type": "V2.1_BEHAVIORAL_FUSION",
                "attack_stage":   stage.value,
                "confidence":     final_result.confidence,
                "timestamp":      datetime.utcnow().isoformat() + "Z",
            },
            "investigation_case": case,
            "explanation": {
                "alert_id":          alert_id,
                "summary":           explanation.summary,
                "reasons":           explanation.reasons,
                "recommended_actions": explanation.recommended_actions,
                "risk_context":      explanation.risk_context,
                "detection_methods": ["CTMC", "Rules", "Isolation_Forest", "Behavioral_Deviation", "Comms", "Trend", "Attack_Chain"],
            },
            "behavioral_context": dev_json,
            "model_breakdown": {
                "ctmc_score": final_result.ctmc_score,
                "rule_score": final_result.rule_score,
                "if_score":   final_result.if_score,
                "pb_score":   final_result.personal_baseline_score,
                "comm_score": final_result.comm_score,
                "trend_score": final_result.trend_score,
                "rule_violations": [
                    {"rule_id": v.rule_id, "rule_name": v.rule_name,
                     "severity": v.severity}
                    for v in violations
                ],
            },
            "timeline": {
                "user_id":        user_id,
                "timeline":       explanation.timeline,
                "timeline_compact": explanation.timeline_compact,
            },
        }
