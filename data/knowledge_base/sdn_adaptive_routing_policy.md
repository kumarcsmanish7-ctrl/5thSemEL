# Policy: Software-Defined Networking (SDN) Adaptive Routing & Link Costing
**Document ID:** POL-NET-SDN-003  
**Classification:** Network Infrastructure Governance  
**Applicability:** Open vSwitch (OvS), Ryu SDN Controller, Mininet Virtual Topology

## 1. Adaptive Routing Architecture
To guarantee uninterrupted CCTV telemetry under network degradation or adversarial attacks, the routing plane operates under software-defined central control.
When link conditions deteriorate, the system departs from static shortest-path Dijkstra to a multi-factor risk-aware cost metric.

## 2. Modified Dijkstra Cost Formulation
For any network link $e = (u, v)$, the link cost is computed dynamically as:
$$\text{Cost}(e) = w_1 \cdot \text{Distance} + w_2 \cdot \text{Latency} + w_3 \cdot \text{Congestion} + w_4 \cdot \text{Security Risk}$$

Default Parameter Weights (Experimentally Normalized):
- $w_1$ (Physical / Hop Cost): 0.15
- $w_2$ (Round Trip Latency in ms): 0.25
- $w_3$ (Bandwidth Utilization / Loss %): 0.30
- $w_4$ (Cybersecurity Risk / DDoS probability): 0.30
Note: $\sum w_i = 1.0$.

## 3. Rerouting Triggers & Flapping Prevention
1. **Reroute Condition:**
   - A reroute trigger occurs when the cost of the active primary path exceeds the cost of a feasible alternate path by a threshold margin $\Delta_{\text{thresh}} \ge 25\%$.
   - A DDoS score $\ge 0.5$ on any link immediately inflates its $w_4$ term to maximum, forcing flow deviation away from the compromised transit switch.
2. **Dampening & Anti-Flapping:**
   - A minimum hold-down timer of 15 seconds is enforced before switching traffic back to the primary link to avoid route oscillations.
3. **SDN Controller Interaction:**
   - The Ryu controller translates calculated path changes into OpenFlow `OFPFC_MODIFY` flow modification entries with high priority (priority=32768) installed into intermediate Open vSwitch instances.
