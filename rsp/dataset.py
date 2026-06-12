"""Dataset loading and validation for the public RSP SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
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


@dataclass
class RSPTimeDependentDataset:
    """Container for time-dependent travel-time samples used by Yang OTAP."""

    network: RoadNetwork
    travel_times: list[np.ndarray]
    od_pairs: list[tuple[int, int]]
    time_step: float = 1.0
    sample_probabilities: np.ndarray | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    edge_order: list[tuple[int, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.travel_times = self._normalize_travel_times(self.travel_times)
        self.od_pairs = [(int(o), int(d)) for o, d in self.od_pairs]
        self.edge_order = [tuple(edge) for edge in (self.edge_order or self.network.edges)]
        self.time_step = float(self.time_step)
        if self.sample_probabilities is not None:
            self.sample_probabilities = np.asarray(self.sample_probabilities, dtype=np.float64)
        self.validate()

    @classmethod
    def from_arrays(
        cls,
        network: RoadNetwork | nx.DiGraph,
        travel_times: np.ndarray | Iterable[np.ndarray],
        od_pairs: Iterable[tuple[int, int]],
        time_step: float = 1.0,
        sample_probabilities: np.ndarray | None = None,
        meta: dict[str, Any] | None = None,
    ) -> "RSPTimeDependentDataset":
        """Build a time-dependent dataset from tensors shaped (K, T, E)."""
        if isinstance(network, nx.DiGraph):
            network = RoadNetwork.from_networkx(network)
        if not isinstance(network, RoadNetwork):
            raise TypeError("network must be a RoadNetwork or networkx.DiGraph")

        return cls(
            network=network,
            travel_times=travel_times,
            od_pairs=list(od_pairs),
            time_step=time_step,
            sample_probabilities=sample_probabilities,
            meta=meta or {},
            edge_order=network.edges,
        )

    @classmethod
    def from_cao_dataset(
        cls,
        dataset: RSPDataset,
        time_profile: np.ndarray | Iterable[float],
        time_step: float = 1.0,
        sample_probabilities: np.ndarray | None = None,
        meta: dict[str, Any] | None = None,
        auto_horizon: bool = True,
        horizon_padding_steps: int = 0,
    ) -> "RSPTimeDependentDataset":
        """Create Yang-style time-dependent tensors from an existing Cao dataset.

        When auto_horizon is enabled, the profile is extended before lifting so
        each configured OD has a conservative sample-wise feasible time horizon.
        """
        profile = cls._normalize_time_profile(time_profile)
        original_steps = int(profile.shape[0])
        if auto_horizon:
            required_steps = cls.recommend_cao_time_horizon_steps(
                dataset=dataset,
                time_profile=profile,
                time_step=time_step,
                padding_steps=horizon_padding_steps,
            )
            profile = cls.extend_time_profile(profile, required_steps)
        travel_times = [
            cls.lift_cao_samples_to_time_dependent(W, profile)
            for W in dataset.travel_times
        ]
        merged_meta = dict(dataset.meta)
        merged_meta.update(meta or {})
        merged_meta.setdefault("source", "cao_dataset_profile_scaled")
        merged_meta.setdefault("auto_horizon", bool(auto_horizon))
        merged_meta.setdefault("input_time_profile_length", original_steps)
        merged_meta.setdefault("time_profile_length", int(profile.shape[0]))
        if auto_horizon:
            merged_meta.setdefault(
                "auto_horizon_added_steps",
                int(profile.shape[0] - original_steps),
            )
            merged_meta.setdefault(
                "auto_horizon_padding_steps",
                int(horizon_padding_steps),
            )
        return cls(
            network=dataset.network,
            travel_times=travel_times,
            od_pairs=dataset.od_pairs,
            time_step=time_step,
            sample_probabilities=sample_probabilities,
            meta=merged_meta,
            edge_order=dataset.edge_order,
        )

    @classmethod
    def from_networkx(
        cls,
        graph: nx.DiGraph,
        od_pairs: Iterable[tuple[int, int]],
        time_profile: np.ndarray | Iterable[float],
        num_samples: int,
        time_step: float = 1.0,
        edge_order: Iterable[tuple[int, int]] | None = None,
        sample_probabilities: np.ndarray | None = None,
        random_seed: int = 42,
        travel_time_source: str = "edge_attributes",
        meta: dict[str, Any] | None = None,
    ) -> "RSPTimeDependentDataset":
        """Build a time-dependent dataset from a NetworkX graph.

        The first implementation supports edge attributes:
        ``mean_time`` plus either ``sigma`` or ``cv``.
        """
        if travel_time_source != "edge_attributes":
            raise ValueError("travel_time_source must be 'edge_attributes'")
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
        profile = cls._normalize_time_profile(time_profile)
        td = cls.generate_from_edge_attributes(
            network=network,
            time_profile=profile,
            num_samples=num_samples,
            seed=random_seed,
        )
        merged_meta = dict(meta or {})
        merged_meta.setdefault("source", "edge_attributes")
        merged_meta.setdefault("random_seed", random_seed)
        return cls(
            network=network,
            travel_times=td,
            od_pairs=list(od_pairs),
            time_step=time_step,
            sample_probabilities=sample_probabilities,
            meta=merged_meta,
            edge_order=frozen_order,
        )

    def validate(self) -> None:
        """Validate tensor shape, edge-order, probabilities, and OD reachability."""
        if len(self.edge_order) != self.network.num_edges:
            raise ValueError(
                f"edge_order length {len(self.edge_order)} does not match "
                f"network.num_edges {self.network.num_edges}"
            )
        if list(self.edge_order) != list(self.network.edges):
            raise ValueError("edge_order must match network.edges exactly")
        if self.time_step <= 0:
            raise ValueError("time_step must be positive")

        if not self.travel_times:
            raise ValueError("travel_times must contain at least one repeat")
        first_shape = self.travel_times[0].shape
        for idx, td in enumerate(self.travel_times):
            if td.ndim != 3:
                raise ValueError(
                    f"travel_times repeat {idx} must be 3D (samples, time_steps, edges), "
                    f"got shape {td.shape}"
                )
            if td.shape[2] != self.network.num_edges:
                raise ValueError(
                    f"travel_times repeat {idx} has {td.shape[2]} edge columns, "
                    f"expected {self.network.num_edges} network edges"
                )
            if td.shape[0] <= 0 or td.shape[1] <= 0:
                raise ValueError(f"travel_times repeat {idx} must have positive sample/time dimensions")
            if np.any(td <= 0):
                raise ValueError(f"travel_times repeat {idx} must contain positive travel times")
            if td.shape[1:] != first_shape[1:]:
                raise ValueError(
                    "all travel_times repeats must share time_steps and edge dimensions"
                )

        if self.sample_probabilities is not None:
            if self.sample_probabilities.ndim != 1:
                raise ValueError("sample_probabilities must be a 1D array")
            if self.sample_probabilities.shape[0] != first_shape[0]:
                raise ValueError(
                    "sample_probabilities length must match num_samples "
                    f"{first_shape[0]}, got {self.sample_probabilities.shape[0]}"
                )
            if np.any(self.sample_probabilities < 0):
                raise ValueError("sample_probabilities must be non-negative")
            if not np.isclose(float(np.sum(self.sample_probabilities)), 1.0):
                raise ValueError("sample_probabilities must sum to 1")

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

    @property
    def num_samples(self) -> int:
        return int(self.travel_times[0].shape[0])

    @property
    def num_time_steps(self) -> int:
        return int(self.travel_times[0].shape[1])

    def deadline_matrix(self, repeat: int = 0) -> np.ndarray:
        """Return W_deadline[sample, edge] = mean_t TD[sample, t, edge]."""
        if repeat < 0 or repeat >= self.num_repeats:
            raise IndexError(
                f"repeat index {repeat} out of range for {self.num_repeats} repeats"
            )
        return self.aggregate_deadline_matrix(self.travel_times[repeat])

    @staticmethod
    def lift_cao_samples_to_time_dependent(
        W: np.ndarray,
        time_profile: np.ndarray | Iterable[float],
    ) -> np.ndarray:
        """Scale static Cao samples by a time profile to form (samples, time, edges)."""
        W = np.asarray(W, dtype=np.float64)
        if W.ndim != 2:
            raise ValueError(f"W must be 2D (samples, edges), got shape {W.shape}")
        if np.any(W <= 0):
            raise ValueError("W must contain positive travel times")
        profile = RSPTimeDependentDataset._normalize_time_profile(time_profile)
        return W[:, None, :] * profile[None, :, None]

    @staticmethod
    def extend_time_profile(
        time_profile: np.ndarray | Iterable[float],
        min_steps: int,
    ) -> np.ndarray:
        """Return a profile with at least min_steps entries.

        Extension repeats the last factor, preserving the user-provided profile
        shape while increasing only the technical time horizon.
        """
        profile = RSPTimeDependentDataset._normalize_time_profile(time_profile)
        min_steps = int(min_steps)
        if min_steps <= profile.shape[0]:
            return profile
        extension = np.full(min_steps - profile.shape[0], profile[-1], dtype=np.float64)
        return np.concatenate([profile, extension])

    @staticmethod
    def recommend_cao_time_horizon_steps(
        dataset: RSPDataset,
        time_profile: np.ndarray | Iterable[float],
        time_step: float,
        padding_steps: int = 0,
    ) -> int:
        """Recommend enough time steps for Cao samples lifted by a time profile."""
        if not isinstance(dataset, RSPDataset):
            raise TypeError("dataset must be an RSPDataset")
        profile = RSPTimeDependentDataset._normalize_time_profile(time_profile)
        time_step = float(time_step)
        if time_step <= 0:
            raise ValueError("time_step must be positive")
        padding_steps = int(padding_steps)
        if padding_steps < 0:
            raise ValueError("padding_steps must be non-negative")

        edge_steps = np.zeros(dataset.network.num_edges, dtype=np.int64)
        scale = float(np.max(profile))
        for W in dataset.travel_times:
            samples = np.asarray(W, dtype=np.float64)
            if samples.ndim != 2:
                raise ValueError(f"Cao travel_times must be 2D, got shape {samples.shape}")
            if samples.shape[1] != dataset.network.num_edges:
                raise ValueError(
                    f"Cao travel_times has {samples.shape[1]} edge columns, "
                    f"expected {dataset.network.num_edges}"
                )
            if np.any(samples <= 0):
                raise ValueError("Cao travel_times must contain positive values")
            candidate = np.ceil((samples * scale) / time_step - 1e-12).astype(np.int64)
            candidate = np.maximum(candidate, 1)
            edge_steps = np.maximum(edge_steps, np.max(candidate, axis=0))

        weighted_graph = nx.DiGraph()
        weighted_graph.add_nodes_from(dataset.network.nodes)
        for edge_idx, (u, v) in enumerate(dataset.network.edges):
            weighted_graph.add_edge(u, v, weight=int(edge_steps[edge_idx]))

        max_path_steps = 0
        for origin, destination in dataset.od_pairs:
            path_steps = nx.shortest_path_length(
                weighted_graph,
                origin,
                destination,
                weight="weight",
            )
            max_path_steps = max(max_path_steps, int(math.ceil(path_steps)))

        return max(int(profile.shape[0]), max_path_steps + padding_steps)

    @staticmethod
    def aggregate_deadline_matrix(td: np.ndarray) -> np.ndarray:
        """Aggregate a time-dependent tensor to Cao-style samples for deadline computation."""
        td = np.asarray(td, dtype=np.float64)
        if td.ndim != 3:
            raise ValueError(f"td must be 3D (samples, time_steps, edges), got shape {td.shape}")
        return np.mean(td, axis=1)

    @staticmethod
    def generate_from_edge_attributes(
        network: RoadNetwork,
        time_profile: np.ndarray | Iterable[float],
        num_samples: int,
        seed: int = 42,
    ) -> np.ndarray:
        """Generate independent lognormal time-dependent samples from edge attributes."""
        num_samples = int(num_samples)
        if num_samples <= 0:
            raise ValueError("num_samples must be positive")
        profile = RSPTimeDependentDataset._normalize_time_profile(time_profile)
        rng = np.random.default_rng(seed)
        td = np.zeros((num_samples, profile.shape[0], network.num_edges), dtype=np.float64)

        for j, (u, v) in enumerate(network.edges):
            attrs = network.graph.edges[u, v]
            if "mean_time" not in attrs:
                raise ValueError(f"edge {(u, v)} missing required mean_time attribute")
            mean_time = float(attrs["mean_time"])
            if mean_time <= 0:
                raise ValueError(f"edge {(u, v)} mean_time must be positive")

            if "sigma" in attrs:
                sigma = float(attrs["sigma"])
                if sigma <= 0:
                    raise ValueError(f"edge {(u, v)} sigma must be positive")
            elif "cv" in attrs:
                cv = float(attrs["cv"])
                if cv <= 0:
                    raise ValueError(f"edge {(u, v)} cv must be positive")
                sigma = float(np.sqrt(np.log1p(cv ** 2)))
            else:
                raise ValueError(f"edge {(u, v)} must define sigma or cv")

            for t, factor in enumerate(profile):
                target_mean = mean_time * float(factor)
                mu = np.log(target_mean) - (sigma ** 2) / 2.0
                td[:, t, j] = rng.lognormal(mu, sigma, size=num_samples)
        return td

    @staticmethod
    def _normalize_travel_times(
        travel_times: np.ndarray | Iterable[np.ndarray],
    ) -> list[np.ndarray]:
        if isinstance(travel_times, np.ndarray):
            if travel_times.ndim == 3:
                return [np.asarray(travel_times, dtype=np.float64)]
            if travel_times.ndim == 4:
                return [np.asarray(td, dtype=np.float64) for td in travel_times]
            raise ValueError(
                "travel_times ndarray must be 3D (K, T, E) or 4D (R, K, T, E), "
                f"got shape {travel_times.shape}"
            )

        normalized = [np.asarray(td, dtype=np.float64) for td in travel_times]
        return normalized

    @staticmethod
    def _normalize_time_profile(time_profile: np.ndarray | Iterable[float]) -> np.ndarray:
        profile = np.asarray(time_profile, dtype=np.float64)
        if profile.ndim != 1:
            raise ValueError("time_profile must be a 1D array")
        if profile.shape[0] <= 0:
            raise ValueError("time_profile must contain at least one time step")
        if np.any(profile <= 0):
            raise ValueError("time_profile must contain positive values")
        return profile
