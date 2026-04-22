import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ComputeHub-Topo")

@dataclass
class NodeCoordinate:
    node_id: str
    lat: float
    lon: float
    load: float # 0.0 to 1.0
    status: str # "ONLINE", "SINKING", "SENSING"

class GlobalTopologyMap:
    """
    Soul-Engine: Global Neural Interface
    Transforms digital compute nodes into physical coordinates.
    """
    def __init__(self):
        self.nodes: Dict[str, NodeCoordinate] = {}
        self.regions = {
            "US-East": {"lat": 38.0, "lon": -77.0},
            "US-West": {"lat": 37.0, "lon": -122.0},
            "EU-West": {"lat": 51.0, "lon": -0.1},
            "Asia-East": {"lat": 35.0, "lon": 139.0},
            "Asia-South": {"lat": 19.0, "lon": 72.0},
        }

    def update_node(self, node_id: str, region: str, load: float, status: str = "ONLINE"):
        reg = self.regions.get(region, {"lat": 0.0, "lon": 0.0})
        # Add slight random jitter to coordinates so nodes don't overlap on map
        self.nodes[node_id] = NodeCoordinate(
            node_id=node_id,
            lat=reg["lat"] + random.uniform(-1.0, 1.0),
            lon=reg["lon"] + random.uniform(-1.0, 1.0),
            load=load,
            status=status
        )

    def get_topology_snapshot(self):
        """Returns a format suitable for the Web Dashboard (GeoJSON-like)"""
        snapshot = []
        for node_id, coord in self.nodes.items():
            snapshot.append({
                "id": node_id,
                "coords": [coord.lat, coord.lon],
                "metrics": {"load": coord.load, "status": coord.status},
                "color": "green" if coord.status == "ONLINE" else "red" if coord.status == "SINKING" else "yellow"
            })
        return snapshot

if __name__ == "__main__":
    # Simulation of Global Topology
    topo = GlobalTopologyMap()
    
    # Simulate nodes globally
    topo.update_node("gpu-ny-01", "US-East", 0.4)
    topo.update_node("gpu-sf-01", "US-West", 0.8)
    topo.update_node("gpu-lon-01", "EU-West", 0.2)
    topo.update_node("gpu-tok-01", "Asia-East", 0.9, status="SINKING")
    topo.update_node("gpu-mum-01", "Asia-South", 0.1)
    
    print("\n--- Global Compute Hub Topology Snapshot ---")
    for node in topo.get_topology_snapshot():
        print(f"Node {node['id']} | Coords: {node['coords']} | Load: {node['metrics']['load']} | Status: {node['metrics']['status']}")
