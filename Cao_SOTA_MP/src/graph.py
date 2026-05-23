"""Road network graph modeling and incidence matrix construction."""

from pathlib import Path
import numpy as np
import networkx as nx
from dataclasses import dataclass


@dataclass
class RoadNetwork:
    """A directed road network graph with incidence matrix support."""

    graph: nx.DiGraph
    nodes: list[int]
    edges: list[tuple[int, int]]

    @classmethod
    def from_networkx(cls, G: nx.DiGraph) -> "RoadNetwork":
        nodes = sorted(G.nodes())
        edges = list(G.edges())
        return cls(graph=G, nodes=nodes, edges=edges)

    @classmethod
    def load(cls, path: str | Path) -> "RoadNetwork":
        """Load network from npz file."""
        data = np.load(path)
        num_nodes = int(data["num_nodes"])
        edges_arr = data["edges"]
        G = nx.DiGraph()
        G.add_nodes_from(range(num_nodes))
        G.add_edges_from(edges_arr.tolist())
        return cls.from_networkx(G)

    def save(self, path: str | Path) -> None:
        """Save network to npz file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path,
                 num_nodes=self.num_nodes,
                 edges=np.array(self.edges, dtype=np.int32))

    @property
    def num_nodes(self) -> int:
        return len(self.nodes)

    @property
    def num_edges(self) -> int:
        return len(self.edges)

    def node_index(self, node: int) -> int:
        return self.nodes.index(node)

    def edge_index(self, edge: tuple[int, int]) -> int:
        return self.edges.index(edge)

    def incidence_matrix(self) -> np.ndarray:
        """Build node-arc incidence matrix M (|V| x |L|).

        M[v, l] = +1 if edge l leaves node v
        M[v, l] = -1 if edge l enters node v
        """
        M = np.zeros((self.num_nodes, self.num_edges), dtype=np.float64)
        for j, (u, v) in enumerate(self.edges):
            M[self.node_index(u), j] = 1.0
            M[self.node_index(v), j] = -1.0
        return M

    def od_vector(self, origin: int, destination: int) -> np.ndarray:
        """Build OD vector b (|V| x 1).

        b[o] = +1, b[d] = -1, rest = 0.
        """
        b = np.zeros(self.num_nodes, dtype=np.float64)
        b[self.node_index(origin)] = 1.0
        b[self.node_index(destination)] = -1.0
        return b

    def enumerate_paths(self, origin: int, destination: int, cutoff: int = 15) -> list[list[int]]:
        """Enumerate all simple paths (for ground-truth on small graphs)."""
        return list(nx.all_simple_paths(self.graph, origin, destination, cutoff=cutoff))

    def path_to_x(self, path: list[int]) -> np.ndarray:
        """Convert a node-sequence path to edge selection vector x."""
        x = np.zeros(self.num_edges, dtype=np.float64)
        for i in range(len(path) - 1):
            edge = (path[i], path[i + 1])
            x[self.edge_index(edge)] = 1.0
        return x
