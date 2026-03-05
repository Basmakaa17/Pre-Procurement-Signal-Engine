"""
Intelligence module for LLM classification, rule-based classification, signal detection, and RFP prediction
"""
from app.intelligence.classifier import ClassificationResult, GrantClassifier
from app.intelligence.rule_classifier import HybridClassifier
from app.intelligence.signal_detector import SignalDetector, SignalResult, run_full_intelligence_pipeline
from app.intelligence.rfp_predictor import predict_rfps, predict_rfps_for_signal, GrantRFPForecast, RFPPrediction

__all__ = [
    "GrantClassifier",
    "HybridClassifier",
    "ClassificationResult",
    "SignalDetector",
    "SignalResult",
    "run_full_intelligence_pipeline",
    "predict_rfps",
    "predict_rfps_for_signal",
    "GrantRFPForecast",
    "RFPPrediction",
]
