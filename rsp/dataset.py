"""Dataset loading and validation for the public RSP SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import networkx as nx
import numpy as np
import yaml

from Cao_SOTA_MP.src.graph import RoadNetwork


@dataclass
class RSPDataset:
    """Container for a road network, travel-time samples, and OD pairs."""

    network: RoadNetwork
    travel_times: list[np.ndarray]
    od_pairs: list[tuple[int, int]]
    meta: dict[str, Any] = field(default_factory=dict)
    edge_order: list[tuple[int, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.travel_times = self._normalize_travel_times(self.travel_times)
        self.od_pairs = [(int(o), int(d)) for o, d in self.od_pairs]
        self.edge_order = [tuple(edge) for edge in (self.edge_order or self.network.edges)]
        self.validate()

    @classmethod
    def from_directory(cls, path: str | Path) -> "RSPDataset":
        """Load an existing generated dataset directory."""
        path = Path(path)
        return cls.from_files(
            network_file=path / "network.npz",
            travel_times_file=path / "travel_times.npz",
            od_pairs_file=path / "od_pairs.npy",
            meta_file=path / "meta.yaml",
        )

    @classmethod
    def from_files(
        cls,
        network_file: str | Path,
        travel_times_file: str | Path,
        od_pairs_file: str | Path,
        meta_file: str | Path | None = None,
    ) -> "RSPDataset":
        """Load a dataset from explicit file paths."""
        network = RoadNetwork.load(network_file)
        od_pairs = np.load(od_pairs_file).tolist()
        travel_times = cls._load_travel_times_file(travel_times_file)

        meta: dict[str, Any] = {}
        if meta_file is not None and Path(meta_file).exists():
            with open(meta_file, encoding="utf-8") as f:
                meta = yaml.safe_load(f) or {}

        return cls(
            network=network,
            travel_times=travel_times,
            od_pairs=od_pairs,
            meta=meta,
            edge_order=network.edges,
        )

    @classmethod
    def from_arrays(
        cls,
        network: RoadNetwork | nx.DiGraph,
        travel_times: np.ndarray | Iterable[np.ndarray],
        od_pairs: Iterable[tuple[int, int]],
        meta: dict[str, Any] | None = None,
    ) -> "RSPDataset":
        """Build a dataset from in-memory arrays."""
        if isinstance(network, nx.DiGraph):
            network = RoadNetwork.from_networkx(network)
        if not isinstance(network, RoadNetwork):
            raise TypeError("network must be a RoadNetwork or networkx.DiGraph")

        return cls(
            network=network,
            travel_times=cls._normalize_travel_times(travel_times),
            od_pairs=list(od_pairs),
            meta=meta or {},
            edge_order=network.edges,
        )

    @classmethod
    def from_networkx(
        cls,
        graph: nx.DiGraph,
        travel_times: np.ndarray | Iterable[np.ndarray],
        od_pairs: Iterable[tuple[int, int]],
        edge_order: Iterable[tuple[int, int]] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> "RSPDataset":
        """Build a dataset from a NetworkX graph and freeze edge order."""
        if not isinstance(graph, nx.DiGraph):
            raise TypeError("graph must be a networkx.DiGraph")

        frozen_order = [tuple(edge) for edge in (edge_order or list(graph.edges()))]
        missing_edges = [edge for edge in frozen_order if not graph.has_edge(*edge)]
        if missing_edges:
            raise ValueError(f"edge_order contains edges not present in graph: {missing_edges[:3]}")

        ordered_graph = nx.DiGraph()
        ordered_graph.add_nodes_from(graph.nodes(data=True))
        for u, v in frozen_order:
            ordered_graph.add_edge(u, v, **dict(graph.edges[u, v]))

        network = RoadNetwork(
            graph=ordered_graph,
            nodes=sorted(ordered_graph.nodes()),
            edges=frozen_order,
        )
        return cls(
            network=network,
            travel_times=cls._normalize_travel_times(travel_times),
            od_pairs=list(od_pairs),
            meta=meta or {},
            edge_order=frozen_order,
        )

    def save(self, path: str | Path) -> None:
        """Save the dataset in the existing Cao_SOTA_MP directory format."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        self.network.save(path / "network.npz")
        np.save(path / "od_pairs.npy", np.array(self.od_pairs, dtype=np.int32))
        np.savez(
            path / "travel_times.npz",
            **{f"repeat_{idx:02d}": W for idx, W in enumerate(self.travel_times)},
        )
        with open(path / "meta.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(self.meta, f, sort_keys=False)

    def validate(self) -> None:
        """Validate shape, edge-order, and OD reachability invariants."""
        if len(self.edge_order) != self.network.num_edges:
            raise ValueError(
                f"edge_order length {len(self.edge_order)} does not match "
                f"network.num_edges {self.network.num_edges}"
            )
        if list(self.edge_order) != list(self.network.edges):
            raise ValueError("edge_order must match network.edges exactly")

        if not self.travel_times:
            raise ValueError("travel_times must contain at least one repeat")
        for idx, W in enumerate(self.travel_times):
            if W.ndim != 2:
                raise ValueError(f"travel_times repeat {idx} must be 2D, got shape {W.shape}")
            if W.shape[1] != self.network.num_edges:
                raise ValueError(
                    f"travel_times repeat {idx} has {W.shape[1]} columns, "
                    f"expected {self.network.num_edges} network edges"
                )

        node_set = set(self.network.nodes)
        for od_idx, (origin, destination) in enumerate(self.od_pairs):
            if origin not in node_set or destination not in node_set:
                raise ValueError(
                    f"OD pair {od_idx} contains node outside network: "
                    f"({origin}, {destination})"
                )
            if origin == destination:
                raise ValueError(f"OD pair {od_idx} has identical origin and destination")
            if not nx.has_path(self.network.graph, origin, destination):
                raise ValueError(f"OD pair {od_idx} is not reachable: ({origin}, {destination})")

    @property
    def num_repeats(self) -> int:
        return len(self.travel_times)

    @property
    def num_od_pairs(self) -> int:
        return len(self.od_pairs)

    @staticmethod
    def _normalize_travel_times(
        travel_times: np.ndarray | Iterable[np.ndarray],
    ) -> list[np.ndarray]:
        if isinstance(travel_times, np.ndarray):
            if travel_times.ndim == 2:
                return [np.asarray(travel_times, dtype=np.float64)]
            if travel_times.ndim == 3:
                return [np.asarray(W, dtype=np.float64) for W in travel_times]
            raise ValueError(
                "travel_times ndarray must be 2D (N, E) or 3D (R, N, E), "
                f"got shape {travel_times.shape}"
            )

        normalized = [np.asarray(W, dtype=np.float64) for W in travel_times]
        return normalized

    @staticmethod
    def _load_travel_times_file(path: str | Path) -> list[np.ndarray]:
        data = np.load(path)
        repeats = []
        idx = 0
        while f"repeat_{idx:02d}" in data:
            repeats.append(np.asarray(data[f"repeat_{idx:02d}"], dtype=np.float64))
            idx += 1
        if not repeats:
            keys = sorted(data.files)
            repeats = [np.asarray(data[key], dtype=np.float64) for key in keys]
        return repeats
