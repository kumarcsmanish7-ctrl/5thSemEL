"""
Automated Verification and Unit Test Suite for Member 3 Deliverables.
Tests:
1. RAG Knowledge Base Loading & Document Chunking
2. Semantic Retrieval Engine (Similarity matching)
3. RAG Mitigation Generation
4. Modified Dijkstra Dynamic Routing (Normal vs DDoS Rerouting)
5. Member 1 & Member 2 Interface Schemas
"""
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.rag_engine import RAGSecurityEngine
from src.dijkstra_router import CyberResilientRouter
from src.mock_streams import MockStreamManager
from src import rag_engine as rag_module
from fastapi.testclient import TestClient
from src.integration_api import app as integration_app, LATEST_STATE

def test_rag_pipeline():
    print("--> Testing RAG Engine...")
    rag = RAGSecurityEngine()
    assert len(rag.chunks) > 0, f"Expected chunks, found {len(rag.chunks)}"
    print(f"    [OK] Loaded {len(rag.chunks)} chunks from knowledge base.")

    # Test retrieval for DDoS
    query = "DDoS attack packet flood SDN adaptive routing"
    retrieved = rag.retrieve_context(query, top_k=2)
    assert len(retrieved) > 0, "No chunks retrieved for DDoS query"
    assert retrieved[0]["similarity_score"] > 0, "Retrieved chunks did not match the query"
    if rag.use_chroma:
        assert rag.collection.count() == len(rag.chunks), "ChromaDB index is missing knowledge chunks"
    print(f"    [OK] Retrieved {len(retrieved)} relevant chunks for '{query}'. Top score: {retrieved[0]['similarity_score']}")

    # Test mitigation response generation
    alert = {
        "alert_type": "DDoS SYN Flood",
        "severity": "CRITICAL",
        "source": "SW-2",
        "details": "Packet rate > 2000 pps, latency > 90ms"
    }
    response = rag.generate_mitigation_response(alert)
    assert "immediate_actions" in response
    assert len(response["immediate_actions"]) > 0
    assert response["retrieved_sources"], "Mitigation response was not grounded in knowledge documents"
    assert len(response["retrieved_sources"]) == len(set(response["retrieved_sources"]))
    print(f"    [OK] Mitigation plan generated successfully: {len(response['immediate_actions'])} actions recommended.")

def test_rag_falls_back_when_chroma_client_fails():
    if not rag_module.CHROMA_AVAILABLE:
        return

    with patch.object(
        rag_module.chromadb,
        "PersistentClient",
        side_effect=ValueError("simulated ChromaDB startup failure")
    ):
        rag = RAGSecurityEngine()

    assert rag.use_chroma is False
    assert rag.retrieval_backend == "TF-IDF"
    assert rag.retrieve_context("DDoS mitigation", top_k=1)
    print("    [OK] Falls back to TF-IDF if ChromaDB cannot start.")

def test_router_pipeline():
    print("--> Testing Modified Dijkstra Router...")
    router = CyberResilientRouter()
    
    # 1. Normal path
    res_normal = router.calculate_optimal_path(source="CAM-01", destination="NVR-SRV")
    assert res_normal["success"] is True
    print(f"    [OK] Normal path: {' -> '.join(res_normal['path'])} (Cost: {res_normal['total_cost']})")

    # 2. Simulate Attack on SW-1 <-> SW-2
    router.apply_network_attack(("SW-1", "SW-2"), risk_score=1.0, latency_spike=90.0, congestion=0.95)
    res_attack = router.calculate_optimal_path(source="CAM-01", destination="NVR-SRV")
    assert res_attack["success"] is True
    print(f"    [OK] Path under attack: {' -> '.join(res_attack['path'])} (Cost: {res_attack['total_cost']})")
    assert "SW-2" not in res_attack["path"] or "SW-3" in res_attack["path"], "Router failed to divert from attacked link"
    print("    [OK] Adaptive rerouting successfully diverted traffic away from compromised link!")

def test_mock_streams():
    print("--> Testing Member 1 & Member 2 Mock Streams...")
    mgr = MockStreamManager()
    
    # Member 1 Video event
    v_event = mgr.get_member1_video_event()
    assert "timestamp" in v_event and "anomaly_score" in v_event and "status" in v_event
    print(f"    [OK] Member 1 Video Interface Output: {v_event['status']} (Score: {v_event['anomaly_score']})")

    # Member 2 Network event
    n_event = mgr.get_member2_network_event()
    assert "timestamp" in n_event and "attack_status" in n_event and "traffic_rate" in n_event and "latency" in n_event and "routing_status" in n_event
    print(f"    [OK] Member 2 Network Interface Output: {n_event['attack_status']} (Rate: {n_event['traffic_rate']} pps, Latency: {n_event['latency']} ms)")

def test_integration_api():
    print("--> Testing Member 1 & Member 2 Live Integration API...")
    original_state = deepcopy(LATEST_STATE)
    client = TestClient(integration_app)
    try:
        initial_state = client.get("/api/state").json()
        assert initial_state["video_event"] is None
        assert initial_state["network_event"] is None
        assert initial_state["alerts_history"] == []
        assert initial_state["video_history"] == []
        assert initial_state["network_history"] == []
        assert initial_state["routing_weights"] == {
            "distance": 0.15,
            "latency": 0.25,
            "congestion": 0.30,
            "security_risk": 0.30,
        }

        weights_response = client.put("/api/network/routing-weights", json={
            "distance": 0.20,
            "latency": 0.25,
            "congestion": 0.30,
            "security_risk": 0.25,
        })
        assert weights_response.status_code == 200
        assert client.get("/api/state").json()["routing_weights"]["distance"] == 0.20
        invalid_weights_response = client.put("/api/network/routing-weights", json={
            "distance": 1.1,
            "latency": 0.25,
            "congestion": 0.30,
            "security_risk": 0.25,
        })
        assert invalid_weights_response.status_code == 422
        invalid_total_response = client.put("/api/network/routing-weights", json={
            "distance": 0.20,
            "latency": 0.20,
            "congestion": 0.20,
            "security_risk": 0.20,
        })
        assert invalid_total_response.status_code == 422

        video_response = client.post("/api/video/alert", json={
            "timestamp": "2026-11-22 10:30:00",
            "anomaly_score": 0.85,
            "status": "ANOMALY_DETECTED",
            "class_name": "person",
            "confidence": 0.94,
            "camera_id": "CAM-01"
        })
        assert video_response.status_code == 200
        assert video_response.json()["status"] == "success"

        network_response = client.post("/api/network/alert", json={
            "timestamp": "2026-11-22 10:31:00",
            "attack_status": "DDOS_ATTACK_DETECTED",
            "traffic_rate": 2400.0,
            "latency": 92.5,
            "packet_loss_pct": 14.2,
            "routing_status": "ADAPTIVE_REROUTED",
            "active_path": "CAM-01 -> SW-1 -> SW-3 -> SW-4 -> NVR-SRV",
            "source": "SW-2",
            "severity": "CRITICAL"
        })
        assert network_response.status_code == 200

        state_response = client.get("/api/state")
        assert state_response.status_code == 200
        state = state_response.json()
        assert state["video_event"]["status"] == "ANOMALY_DETECTED"
        assert state["video_event"]["severity"] == "HIGH"
        assert state["network_event"]["attack_status"] == "DDOS_ATTACK_DETECTED"
        assert state["network_event"]["source"] == "SW-2"
        assert len(state["video_history"]) == 1
        assert state["video_history"][0]["anomaly_score"] == 0.85
        assert len(state["network_history"]) == 1
        assert len(state["alerts_history"]) == 2
        print("    [OK] Video and network alerts are accepted and exposed to the dashboard.")

        rag_status = client.get("/api/rag/status")
        assert rag_status.status_code == 200
        assert rag_status.json()["knowledge_chunks"] > 0
        rag_response = client.post("/api/rag/query", json={
            "query": "DDoS mitigation for preserving camera recording"
        })
        assert rag_response.status_code == 200
        assert rag_response.json()["retrieved_chunks"]
    finally:
        LATEST_STATE.clear()
        LATEST_STATE.update(original_state)

if __name__ == "__main__":
    print("==================================================")
    print("  RUNNING VERIFICATION SUITE FOR MEMBER 3 (RAG & DASHBOARD)")
    print("==================================================")
    test_rag_pipeline()
    test_rag_falls_back_when_chroma_client_fails()
    test_router_pipeline()
    test_mock_streams()
    test_integration_api()
    print("==================================================")
    print("  ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")
