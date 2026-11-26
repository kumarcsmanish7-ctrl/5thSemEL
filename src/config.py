"""
Configuration module for Cyber-Resilient CCTV System.
Stores global constants, weights for Modified Dijkstra routing,
risk thresholds, and file paths.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"
CHROMA_PERSIST_DIR = DATA_DIR / "chroma_db"

# Ensure directories exist
KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

# Modified Dijkstra Weights (must sum to 1.0)
ROUTING_WEIGHTS = {
    "distance": 0.15,
    "latency": 0.25,
    "congestion": 0.30,
    "security_risk": 0.30
}

# Alert Thresholds
THRESHOLDS = {
    "video_anomaly_low": 0.40,
    "video_anomaly_medium": 0.60,
    "video_anomaly_high": 0.80,
    "ddos_traffic_rate_pps": 800,  # packets per second
    "ddos_latency_ms": 100,        # milliseconds
    "ddos_packet_loss_pct": 5.0    # percent
}

# Network Topology Definition (Default 4-switch mesh for CCTV)
DEFAULT_TOPOLOGY = {
    "nodes": ["CAM-01", "CAM-02", "SW-1", "SW-2", "SW-3", "SW-4", "NVR-SRV"],
    "edges": [
        ("CAM-01", "SW-1", {"distance": 1.0, "latency": 2.0, "congestion": 0.05, "security_risk": 0.0}),
        ("CAM-02", "SW-1", {"distance": 1.0, "latency": 2.5, "congestion": 0.05, "security_risk": 0.0}),
        ("SW-1", "SW-2", {"distance": 2.0, "latency": 5.0, "congestion": 0.10, "security_risk": 0.0}),
        ("SW-1", "SW-3", {"distance": 3.0, "latency": 8.0, "congestion": 0.08, "security_risk": 0.0}),
        ("SW-2", "SW-4", {"distance": 2.0, "latency": 6.0, "congestion": 0.12, "security_risk": 0.0}),
        ("SW-3", "SW-4", {"distance": 2.5, "latency": 7.0, "congestion": 0.09, "security_risk": 0.0}),
        ("SW-4", "NVR-SRV", {"distance": 1.0, "latency": 3.0, "congestion": 0.05, "security_risk": 0.0}),
        # Redundant cross-link for adaptive routing resilience
        ("SW-2", "SW-3", {"distance": 1.5, "latency": 4.0, "congestion": 0.07, "security_risk": 0.0})
    ]
}
