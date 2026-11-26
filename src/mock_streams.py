"""
Mock Streams and Ingestion Interfaces for Member 1 and Member 2.
Adheres strictly to the sprint-agreed field interfaces:
- Member 1 (Video): timestamp, anomaly_score, status, class_name, confidence
- Member 2 (Network): timestamp, attack_status, traffic_rate, latency, routing_status
Allows seamless live demo testing even before teammates' code is plugged in.
"""
import time
import random
from datetime import datetime
from typing import Dict, Any

class MockStreamManager:
    def __init__(self):
        self.attack_active = False
        self.video_anomaly_active = False
        self.attack_target_link = ("SW-1", "SW-2")

    def toggle_ddos_attack(self, active: bool = None):
        if active is None:
            self.attack_active = not self.attack_active
        else:
            self.attack_active = active
        return self.attack_active

    def toggle_video_anomaly(self, active: bool = None):
        if active is None:
            self.video_anomaly_active = not self.video_anomaly_active
        else:
            self.video_anomaly_active = active
        return self.video_anomaly_active

    def get_member1_video_event(self) -> Dict[str, Any]:
        """
        Member 1 Output Interface:
        timestamp, anomaly_score, status
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.video_anomaly_active:
            score = round(random.uniform(0.78, 0.96), 3)
            status = "ANOMALY_DETECTED"
            event_type = random.choice([
                "Unauthorized Zone Intrusion",
                "Perimeter Loitering Detected",
                "Camera Lens Tampering / Occlusion",
                "Unusual Rapid Movement in Restricted Area"
            ])
            confidence = round(random.uniform(0.85, 0.98), 2)
        else:
            score = round(random.uniform(0.05, 0.28), 3)
            status = "NORMAL"
            event_type = "Routine Surveillance"
            confidence = round(random.uniform(0.92, 0.99), 2)

        return {
            "timestamp": now,
            "anomaly_score": score,
            "status": status,
            "event_type": event_type,
            "confidence": confidence,
            "camera_id": "CAM-01 (Main Perimeter)",
            "frame_id": int(time.time() * 10) % 100000
        }

    def get_member2_network_event(self) -> Dict[str, Any]:
        """
        Member 2 Output Interface:
        timestamp, attack_status, traffic_rate, latency, routing_status
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.attack_active:
            attack_status = "DDOS_ATTACK_DETECTED"
            traffic_rate = random.randint(1800, 3500)  # packets per second
            latency = round(random.uniform(75.0, 180.0), 2)  # ms
            packet_loss = round(random.uniform(8.5, 24.0), 1)  # %
            routing_status = "ADAPTIVE_REROUTED"
            active_path = ["CAM-01", "SW-1", "SW-3", "SW-4", "NVR-SRV"]
            attack_type = random.choice(["SYN Flood", "UDP Amplification", "IoT Mirai Botnet Burst"])
        else:
            attack_status = "NORMAL"
            traffic_rate = random.randint(120, 320)  # pps
            latency = round(random.uniform(3.5, 9.2), 2)  # ms
            packet_loss = round(random.uniform(0.0, 0.4), 1)
            routing_status = "PRIMARY_ROUTE"
            active_path = ["CAM-01", "SW-1", "SW-2", "SW-4", "NVR-SRV"]
            attack_type = "None"

        return {
            "timestamp": now,
            "attack_status": attack_status,
            "traffic_rate": traffic_rate,
            "latency": latency,
            "packet_loss_pct": packet_loss,
            "routing_status": routing_status,
            "active_path": " -> ".join(active_path),
            "attack_type": attack_type,
            "affected_switch": "SW-2 (Primary Aggregation)" if self.attack_active else "None"
        }
