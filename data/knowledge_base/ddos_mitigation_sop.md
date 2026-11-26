# Standard Operating Procedure: CCTV Network DDoS Mitigation & Link Flooding
**Document ID:** SOP-SEC-NET-001  
**Classification:** Internal Cybersecurity Operational Guideline  
**Applicability:** IP Surveillance Cameras, NVRs, SDN Switches, Ryu Controllers

## 1. Threat Overview
Distributed Denial of Service (DDoS) attacks against CCTV networks (such as SYN Floods, UDP Amplification, ICMP Echo Floods, and Mirai-like botnet attacks) saturate network switches and links connecting IP cameras to Network Video Recorders (NVRs) and Security Operations Centers (SOC). 
Symptoms include:
- Abrupt spike in packet arrival rates (> 1,000 pps per link).
- Excessive video transmission latency (> 150 ms) and frame dropping/freezing.
- Severe link utilization (> 85%) and packet loss (> 10%).

## 2. Immediate Containment & Mitigation Protocols
1. **Adaptive SDN Rerouting:**
   - Immediately instruct the SDN (Ryu/OpenFlow) Controller to recompute flow paths using the **Modified Dijkstra Algorithm**.
   - Ensure the routing cost formula penalizes malicious links:
     `Link Cost = w1*(Distance) + w2*(Latency) + w3*(Congestion) + w4*(Security Risk)`
   - Dynamically redirect legitimate CCTV RTP/RTSP video packets to alternate redundant routes (e.g., secondary switches or backup aggregation links).

2. **Flow Rule Insertion & Rate Limiting:**
   - Execute OpenFlow meter table policies on ingress switches to throttle high-volume traffic from offending IP subnets.
   - Drop unauthorized TCP SYN or UDP traffic exceeding normal operational baselines (baseline CCTV camera stream: 2–8 Mbps per 1080p stream).

3. **Isolation of Compromised Camera Nodes:**
   - If an IoT CCTV camera IP exhibits anomalous outbound scanning traffic, quarantine the switch port immediately into a restricted VLAN.
   - Verify camera firmware and check for default credential exploitation (Mirai signature).

4. **Monitoring & Service Restoration:**
   - Continuously evaluate packet delivery ratio (PDR) and frame jitter.
   - Once traffic rate stabilizes below the 200 pps threshold and latency returns under 30 ms, restore primary routing paths progressively.
