"""
Modified Dijkstra Routing Algorithm for SDN-enabled Cyber-Resilient CCTV.
Calculates the dynamic cost of each link using:
Cost = w1 * Distance + w2 * Latency + w3 * Congestion + w4 * Security_Risk
"""
import heapq
import networkx as nx
from typing import Dict, List, Tuple, Any
from .config import ROUTING_WEIGHTS, DEFAULT_TOPOLOGY

class CyberResilientRouter:
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or ROUTING_WEIGHTS.copy()
        self.graph = nx.Graph()
        self.reset_to_default()

    def reset_to_default(self):
        """Initializes graph with default CCTV network topology."""
        self.graph.clear()
        for node in DEFAULT_TOPOLOGY["nodes"]:
            self.graph.add_node(node)
        for u, v, attrs in DEFAULT_TOPOLOGY["edges"]:
            self.graph.add_edge(u, v, **attrs)

    def compute_link_cost(self, attrs: Dict[str, float]) -> float:
        """
        Computes link cost according to the project's formula:
        Cost = w1*(distance) + w2*(latency) + w3*(congestion) + w4*(security_risk)
        Normalizes metrics to a 0-10 scale for fair weighting.
        """
        w1 = self.weights.get("distance", 0.15)
        w2 = self.weights.get("latency", 0.25)
        w3 = self.weights.get("congestion", 0.30)
        w4 = self.weights.get("security_risk", 0.30)

        dist = attrs.get("distance", 1.0)
        # Latency normalized (assumes 0 - 50ms scale)
        latency = attrs.get("latency", 5.0) / 10.0
        # Congestion (0.0 to 1.0 normalized)
        congestion = attrs.get("congestion", 0.1) * 10.0
        # Security risk (0.0 normal, 1.0 under active DDoS attack)
        sec_risk = attrs.get("security_risk", 0.0) * 15.0

        cost = (w1 * dist) + (w2 * latency) + (w3 * congestion) + (w4 * sec_risk)
        return round(max(0.01, cost), 4)

    def apply_network_attack(self, target_link: Tuple[str, str], risk_score: float = 1.0, latency_spike: float = 45.0, congestion: float = 0.95):
        """Simulates an active DDoS attack on a specific switch/link."""
        u, v = target_link
        if self.graph.has_edge(u, v):
            self.graph[u][v]["security_risk"] = risk_score
            self.graph[u][v]["latency"] = latency_spike
            self.graph[u][v]["congestion"] = congestion

    def clear_attack(self, target_link: Tuple[str, str]):
        """Restores a link to normal operational state."""
        u, v = target_link
        if self.graph.has_edge(u, v):
            self.graph[u][v]["security_risk"] = 0.0
            self.graph[u][v]["latency"] = 5.0
            self.graph[u][v]["congestion"] = 0.10

    def calculate_optimal_path(self, source: str = "CAM-01", destination: str = "NVR-SRV") -> Dict[str, Any]:
        """
        Modified Dijkstra Algorithm considering composite cost.
        Returns the optimal path, individual link costs, and total cost.
        """
        # Distances map: node -> min_cost
        distances = {node: float('inf') for node in self.graph.nodes}
        previous_nodes = {node: None for node in self.graph.nodes}
        distances[source] = 0.0
        
        pq = [(0.0, source)]
        visited = set()

        while pq:
            current_cost, current_node = heapq.heappop(pq)

            if current_node in visited:
                continue
            visited.add(current_node)

            if current_node == destination:
                break

            for neighbor in self.graph.neighbors(current_node):
                if neighbor in visited:
                    continue
                edge_data = self.graph[current_node][neighbor]
                link_cost = self.compute_link_cost(edge_data)
                new_cost = current_cost + link_cost

                if new_cost < distances[neighbor]:
                    distances[neighbor] = new_cost
                    previous_nodes[neighbor] = current_node
                    heapq.heappush(pq, (new_cost, neighbor))

        # Reconstruct path
        path = []
        curr = destination
        while curr:
            path.append(curr)
            curr = previous_nodes[curr]
        path.reverse()

        if path and path[0] == source:
            edge_details = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i+1]
                attrs = self.graph[u][v]
                cost = self.compute_link_cost(attrs)
                edge_details.append({
                    "from": u,
                    "to": v,
                    "cost": cost,
                    "latency": attrs.get("latency", 0),
                    "congestion": attrs.get("congestion", 0),
                    "security_risk": attrs.get("security_risk", 0)
                })

            return {
                "success": True,
                "path": path,
                "total_cost": round(distances[destination], 3),
                "edge_details": edge_details,
                "is_rerouted": "SW-3" in path if "SW-2" in DEFAULT_TOPOLOGY["nodes"] else False
            }
        else:
            return {"success": False, "path": [], "total_cost": 0.0, "edge_details": [], "is_rerouted": False}

    def get_all_edges_status(self) -> List[Dict[str, Any]]:
        """Returns the status and computed cost of all links in the topology."""
        results = []
        for u, v, attrs in self.graph.edges(data=True):
            cost = self.compute_link_cost(attrs)
            results.append({
                "link": f"{u} <-> {v}",
                "u": u,
                "v": v,
                "cost": cost,
                "latency_ms": attrs.get("latency", 0),
                "congestion_pct": round(attrs.get("congestion", 0) * 100, 1),
                "security_risk": attrs.get("security_risk", 0),
                "is_attacked": attrs.get("security_risk", 0) > 0.4
            })
        return results
