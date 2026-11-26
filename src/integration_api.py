"""REST API endpoints for video and network telemetry integration."""
import math
import time
from functools import lru_cache
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import ROUTING_WEIGHTS, THRESHOLDS
from .rag_engine import RAGSecurityEngine

app = FastAPI(title="Smart CCTV Security Integration Hub")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8501",
        "http://localhost:8501",
    ],
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type"],
)

# Empty event state prevents the dashboard from presenting invented telemetry.
LATEST_STATE = {
    "video_event": None,
    "network_event": None,
    "alerts_history": [],
    "routing_weights": dict(ROUTING_WEIGHTS),
    "video_history": [],
    "network_history": []
}

class VideoAlertPayload(BaseModel):
    timestamp: Optional[str] = None
    anomaly_score: float
    status: str
    class_name: Optional[str] = None
    confidence: Optional[float] = None
    camera_id: Optional[str] = None
    severity: Optional[str] = None

class NetworkAlertPayload(BaseModel):
    timestamp: Optional[str] = None
    attack_status: str
    traffic_rate: float
    latency: float
    routing_status: str
    packet_loss_pct: Optional[float] = None
    active_path: Optional[str] = None
    source: Optional[str] = None
    severity: Optional[str] = None

class RoutingWeightsPayload(BaseModel):
    distance: float = Field(ge=0.0, le=1.0)
    latency: float = Field(ge=0.0, le=1.0)
    congestion: float = Field(ge=0.0, le=1.0)
    security_risk: float = Field(ge=0.0, le=1.0)

class RagQueryPayload(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    alert_data: Optional[Dict[str, Any]] = None

@lru_cache(maxsize=1)
def get_rag_engine():
    return RAGSecurityEngine()

@app.get("/api/health")
def health_check():
    return {"status": "online", "role": "RAG & Live Dashboard Hub", "time": time.time()}

@app.get("/api/state")
def get_current_state():
    return LATEST_STATE

@app.get("/api/rag/status")
def rag_status():
    engine = get_rag_engine()
    return {
        "retrieval_backend": engine.retrieval_backend,
        "knowledge_chunks": len(engine.chunks),
    }

@app.post("/api/rag/query")
def rag_query(payload: RagQueryPayload):
    """Search the security knowledge base or generate guidance for a real alert."""
    engine = get_rag_engine()
    if payload.alert_data:
        response = engine.generate_mitigation_response(
            payload.alert_data,
            user_query=payload.query,
        )
        return {"kind": "recommendation", **response}

    retrieved = engine.retrieve_context(payload.query, top_k=3)
    return {
        "kind": "retrieval",
        "query": payload.query,
        "retrieved_sources": list(dict.fromkeys(
            item["chunk"]["source_file"] for item in retrieved
        )),
        "retrieved_chunks": retrieved,
    }

@app.put("/api/network/routing-weights")
def update_routing_weights(payload: RoutingWeightsPayload):
    """Store operator-selected weights for the network routing service."""
    if not math.isclose(sum(payload.dict().values()), 1.0, abs_tol=0.001):
        raise HTTPException(
            status_code=422,
            detail="Routing weights must sum to 1.0.",
        )
    LATEST_STATE["routing_weights"] = payload.dict()
    return {"status": "success", "routing_weights": LATEST_STATE["routing_weights"]}

@app.post("/api/video/alert")
def receive_video_alert(payload: VideoAlertPayload):
    """Receive a video anomaly detection event."""
    ts = payload.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_anomaly = payload.status.upper() in {"ANOMALY", "ANOMALY_DETECTED", "ALERT"}
    severity = payload.severity
    if is_anomaly and severity is None:
        if payload.anomaly_score >= THRESHOLDS["video_anomaly_high"]:
            severity = "HIGH"
        elif payload.anomaly_score >= THRESHOLDS["video_anomaly_medium"]:
            severity = "MEDIUM"
        else:
            severity = "LOW"
    LATEST_STATE["video_event"] = {
        "timestamp": ts,
        "anomaly_score": payload.anomaly_score,
        "status": payload.status,
        "event_type": payload.class_name,
        "confidence": payload.confidence,
        "camera_id": payload.camera_id,
        "severity": severity
    }
    LATEST_STATE["video_history"].append({
        "timestamp": ts,
        "anomaly_score": payload.anomaly_score,
        "status": payload.status,
        "severity": severity,
        "camera_id": payload.camera_id,
    })
    del LATEST_STATE["video_history"][:-100]
    if is_anomaly:
        LATEST_STATE["alerts_history"].insert(0, {
            "time": ts,
            "type": f"Video Anomaly: {payload.class_name or 'Unspecified event'}",
            "severity": severity or "UNSPECIFIED",
            "source": payload.camera_id,
            "status": "Received"
        })
        del LATEST_STATE["alerts_history"][100:]
    return {"status": "success", "received": payload.dict()}

@app.post("/api/network/alert")
def receive_network_alert(payload: NetworkAlertPayload):
    """Receive a network detection and routing event."""
    ts = payload.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    LATEST_STATE["network_event"] = {
        "timestamp": ts,
        "attack_status": payload.attack_status,
        "traffic_rate": payload.traffic_rate,
        "latency": payload.latency,
        "packet_loss_pct": payload.packet_loss_pct,
        "routing_status": payload.routing_status,
        "active_path": payload.active_path,
        "source": payload.source,
        "severity": payload.severity
    }
    LATEST_STATE["network_history"].append({
        "timestamp": ts,
        "attack_status": payload.attack_status,
        "traffic_rate": payload.traffic_rate,
        "latency": payload.latency,
        "packet_loss_pct": payload.packet_loss_pct,
        "routing_status": payload.routing_status,
        "active_path": payload.active_path,
    })
    del LATEST_STATE["network_history"][:-100]
    if any(term in payload.attack_status.upper() for term in ("DDOS", "ATTACK", "FLOOD")):
        severity = payload.severity or "CRITICAL"
        LATEST_STATE["network_event"]["severity"] = severity
        LATEST_STATE["alerts_history"].insert(0, {
            "time": ts,
            "type": f"Network Attack: {payload.attack_status}",
            "severity": severity,
            "source": payload.source,
            "status": "Received"
        })
        del LATEST_STATE["alerts_history"][100:]
    return {"status": "success", "received": payload.dict()}
