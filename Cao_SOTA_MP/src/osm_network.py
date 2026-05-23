"""Beijing OSM road network loading and conversion to RoadNetwork format.

The network topology is pre-extracted from OpenStreetMap data for central Beijing
(bbox: 39.89-39.94 N, 116.37-116.42 E, major roads only: secondary and above).
Stored as GraphML to avoid runtime Overpass API dependency.
"""

from pathlib import Path

import networkx as nx

from .graph import RoadNetwork

HIGHWAY_SPEED = {
    "motorway": 60.0,
    "motorway_link": 55.0,
    "trunk": 55.0,
    "trunk_link": 50.0,
    "primary": 50.0,
    "primary_link": 45.0,
    "secondary": 40.0,
    "secondary_link": 35.0,
    "tertiary": 35.0,
    "tertiary_link": 30.0,
    "residential": 30.0,
    "unclassified": 30.0,
    "living_street": 20.0,
}

HIGHWAY_CV_RANGE = {
    "motorway": (0.5, 0.8),
    "motorway_link": (0.5, 0.8),
    "trunk": (0.5, 0.8),
    "trunk_link": (0.5, 0.8),
    "primary": (0.5, 0.8),
    "primary_link": (0.6, 0.9),
    "secondary": (0.7, 1.1),
    "secondary_link": (0.7, 1.1),
    "tertiary": (0.7, 1.1),
    "tertiary_link": (0.7, 1.1),
    "residential": (0.9, 1.3),
    "unclassified": (0.9, 1.3),
    "living_street": (0.9, 1.3),
}

DEFAULT_SPEED = 35.0
DEFAULT_CV_RANGE = (0.6, 1.0)


def load_beijing_network() -> RoadNetwork:
    """Load central Beijing road network from pre-extracted OSM data.

    Returns a RoadNetwork with edge attributes:
      - length: float (meters)
      - highway: str (road type, e.g. 'primary', 'secondary')
      - speed: float (km/h, derived from road type)
      - mean_time: float (minutes = length / speed_converted)

    The network covers central Beijing (within ~2nd ring road),
    including secondary roads and above.
    """
    graphml_path = Path(__file__).parent.parent / "data" / "beijing_osm.graphml"
    G = nx.read_graphml(graphml_path)

    # Convert string attributes back to proper types
    G_fixed = nx.DiGraph()
    G_fixed.add_nodes_from(G.nodes())
    for u, v, data in G.edges(data=True):
        length = float(data.get("length", 100.0))
        highway = data.get("highway", "secondary")
        speed = float(data.get("speed", DEFAULT_SPEED))
        mean_time = float(data.get("mean_time", 1.0))
        G_fixed.add_edge(u, v, length=length, highway=highway,
                         speed=speed, mean_time=mean_time)

    return RoadNetwork.from_networkx(G_fixed)


def get_highway_cv_range(highway: str) -> tuple[float, float]:
    """Get CV range for a given highway type."""
    return HIGHWAY_CV_RANGE.get(highway, DEFAULT_CV_RANGE)
