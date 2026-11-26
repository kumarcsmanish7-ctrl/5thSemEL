# Cyber-Resilient CCTV using Adaptive Routing and RAG
**RV College of Engineering | Experiential Learning V Semester (2026-27)**  
**Team 70 (Catalyst)** | **Theme:** SDG 9 (Digital Inclusion and Resilient Infrastructure)  

---

## 🎯 Member 3 Responsibility: RAG & Live Dashboard Integration
**Student:** MONIKA K N (1RV25CI406 - CSE-AIML)  
**Role:** Integration & Security Intelligence Lead  

### Core Objectives:
1. **Knowledge Base Preparation:** Curate Standard Operating Procedures (SOPs) and incident response playbooks for DDoS attacks, camera physical tampering, and SDN routing policies.
2. **Vector Store & Semantic Search:** Chunk, embed, and index security knowledge into a vector database for sub-second semantic retrieval.
3. **RAG-based Mitigation Engine:** Grounded context retrieval and AI recommendations for security operators.
4. **Live SOC / SIEM Dashboard:** Unified React monitoring interface consolidating:
   - Member 1's CCTV video anomaly scores and alerts
   - Member 2's DDoS detection and dynamic SDN Dijkstra routing
   - Real-time incident severity breakdown and interactive copilot

---

## 📁 Repository Structure
```text
d:\5TH_SEM_MAINEL\
├── README.md                          # Project documentation and sprint roadmap
├── requirements.txt                   # Python dependencies
├── app.py                             # Legacy Streamlit dashboard
├── test_pipeline.py                   # Automated verification test suite
├── frontend/                          # React + TypeScript dashboard
├── data/
│   ├── knowledge_base/                # Cybersecurity SOPs & Incident Playbooks
│   │   ├── ddos_mitigation_sop.md
│   │   ├── cctv_physical_anomaly_sop.md
│   │   ├── sdn_adaptive_routing_policy.md
│   │   └── incident_response_playbook.md
│   └── chroma_db/                     # Vector store persistence
└── src/
    ├── __init__.py
    ├── config.py                      # Dijkstra weights, topology, alert thresholds
    ├── dijkstra_router.py             # Modified Dijkstra algorithm engine
    ├── mock_streams.py                # Standalone simulation streams for Member 1 & 2
    ├── rag_engine.py                  # Chunking, vector indexing, retrieval & mitigation generator
    └── integration_api.py             # REST API for Member 1 & 2 data ingestion
```

---

## ✅ Member 3 Deliverable Status

| Deliverable | Status |
| :--- | :--- |
| Knowledge base documents | Prepared in `data/knowledge_base/` |
| Vector indexing and retrieval | Persistent ChromaDB index; Sentence Transformers when model weights are available, TF-IDF fallback otherwise |
| Mitigation recommendations | Retrieval-grounded, deterministic recommendations with source documents |
| React SOC dashboard | Live integration API; explicit waiting and disconnected states |
| Member 1/2 alert ingestion | FastAPI endpoints below; dashboard polls the API every 5 seconds |
| Verification | Run `python test_pipeline.py` to verify RAG, routing, mock streams, and API contracts |

Recommendations are deterministic and grounded in retrieved SOP chunks; this prototype does not call an external generative LLM.

---

## 🚀 Run the Integrated Dashboard

Install dependencies:
```powershell
python -m pip install -r requirements.txt
```

By default, startup uses locally cached Sentence Transformer weights and falls back to ChromaDB-indexed TF-IDF vectors when the model is unavailable. To allow downloading `all-MiniLM-L6-v2` on first run, set:
```powershell
$env:RAG_ALLOW_MODEL_DOWNLOAD = "1"
```

Start the alert ingestion API:
```powershell
uvicorn src.integration_api:app --host 0.0.0.0 --port 8000
```

In another terminal, install and start the React dashboard:
```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:8501`. The Vite development server proxies `/api` requests to `http://127.0.0.1:8000`; the API URL field can be left blank to use this proxy. The dashboard polls for state every five seconds. It does not generate or display simulated detection results. When the API or either detection feed has not connected, the dashboard clearly shows a disconnected or waiting state instead of fabricated measurements. The alert feed can be filtered by severity and searched by incident, source, status, or time. The previous Streamlit dashboard remains available with `streamlit run app.py` if needed.

Member 1 sends video alert metadata and Member 2 sends network and routing metadata to the API endpoints below. The dashboard displays Member 2's reported route; it does not calculate routes, modify SDN rules, or run video detection. A local webcam preview is optional and isolated from the integration pipeline; Member 1's analyzer must send its own results.

The **Modified Dijkstra Weights** controls in the sidebar save the selected values to the integration API; the four values must sum to 1.0. The network routing service can read the current values from `GET /api/state` in the `routing_weights` field and apply them in its routing calculation. Saving the values does not itself execute a route change. If an anomaly alert omits severity, the API derives it from the configured video-score thresholds; network attack alerts default to critical unless severity is supplied.

### Integration endpoints

- `GET /api/health` — API health
- `GET /api/state` — latest video/network events and recent alerts
- `GET /api/rag/status` — retrieval backend and indexed knowledge count
- `POST /api/rag/query` — retrieve guidance or generate alert-grounded recommendations
- `POST /api/video/alert` — Member 1 video alert payload
- `POST /api/network/alert` — Member 2 network alert payload
- `PUT /api/network/routing-weights` — save operator-selected Dijkstra weights for Member 2

Send the JSON payloads shown in the team integration contracts below. Alert history is held in memory and clears when the API restarts. The API has no authentication; expose it only on a trusted lab network, not the public internet.

---

## 🔗 Team Integration Contracts (Rule #1: Freeze Interfaces)

### Member 1 ➔ Member 3 (Video Anomaly Detection)
- **Format:** JSON / Python dictionary
- **Fields:**
  ```json
  {
    "timestamp": "2026-11-22 10:30:00",
    "anomaly_score": 0.85,
    "status": "ANOMALY_DETECTED",
    "class_name": "person",
    "confidence": 0.94,
    "camera_id": "CAM-01",
    "severity": "HIGH"
  }
  ```

### Member 2 ➔ Member 3 (DDoS Detection & Adaptive Routing)
- **Format:** JSON / Python dictionary
- **Fields:**
  ```json
  {
    "timestamp": "2026-11-22 10:30:00",
    "attack_status": "DDOS_ATTACK_DETECTED",
    "traffic_rate": 2400.0,
    "latency": 92.5,
    "packet_loss_pct": 14.2,
    "routing_status": "ADAPTIVE_REROUTED",
    "active_path": "CAM-01 -> SW-1 -> SW-3 -> SW-4 -> NVR-SRV",
    "source": "SW-2",
    "severity": "CRITICAL"
  }
  ```

---

## Integration boundary

The dashboard is a presentation and response-guidance layer. It consumes the shared API state and displays actual received alert metadata. Detection, video-frame analysis, network monitoring, and SDN actions must be supplied by Member 1 and Member 2; no synthetic measurements are presented as live results.
