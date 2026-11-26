# Unified Incident Response Playbook: Cyber-Physical CCTV Security
**Document ID:** PB-CYBER-PHYS-004  
**Classification:** SOC / SIEM Joint Response Playbook  
**Applicability:** Security Operations Center (SOC), CCTV Monitoring Teams, Network Operations

## 1. Joint Cyber-Physical Threat Scenarios

### Scenario A: Coordinated Physical Intrusion + DDoS Network Blinding
- **Attack Vector:** Perpetrators launch a network-level DDoS flood targeting CCTV streaming switches precisely when executing physical perimeter breaches. The intent is to blind monitoring operators and disrupt NVR recording.
- **Automated Response Protocol:**
  1. Trigger immediate alert in SIEM: `CRITICAL: Coordinated Cyber-Physical Attack Detected`.
  2. The Adaptive Routing module shifts video feeds from saturated switches (e.g. Switch S1) to alternate paths (Switch S2 -> S3) to preserve stream continuity.
  3. Video anomaly detection flags physical movement and logs bounding boxes/timestamps locally and sends high-priority frames through available bandwidth.
  4. RAG system generates emergency defense briefing:
     - Isolate victim subnet upstream.
     - Dispatch armed response to physical intrusion zone.
     - Archive volatile flow logs and camera timestamps for forensic evidence.

### Scenario B: IoT Camera Botnet Recruitment & Exfiltration
- **Attack Vector:** Surveillance cameras compromised via Mirai malware or known firmware CVEs, joining external DDoS botnets or leaking video feeds.
- **Automated Response Protocol:**
  1. DDoS detector identifies high outbound connection rates and anomalous destination IPs from camera hosts.
  2. Rate limit or quarantine the affected camera's switch port via Ryu flow-rule drops.
  3. Dispatch physical technician to reset camera credentials and update firmware.
