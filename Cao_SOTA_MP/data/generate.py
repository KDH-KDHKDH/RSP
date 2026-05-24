"""Data generation script for the punctuality problem experiments.

Generates network topology, travel time samples, and OD pairs,
saving them to disk for later use by the experiment runner.

Usage:
    # Presets
    uv run python Cao_SOTA_MP/data/generate.py --preset small
    uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42
    uv run python Cao_SOTA_MP/data/generate.py --preset beijing

    # Custom
    uv run python Cao_SOTA_MP/data/generate.py --nodes 65 --edges 123 --samples 500 --repeats 10 --od-pairs 20 --seed 42 --output data/full/seed42
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.generator import (create_artificial_network, generate_travel_times,
                           generate_beijing_travel_times, random_od_pairs)
from src.osm_network import HIGHWAY_CV_RANGE, load_beijing_network


PRESETS = {
    "small": {"nodes": 10, "edges": 20, "samples": 50, "repeats": 3, "od_pairs": 5},
    "full": {"nodes": 65, "edges": 123, "samples": 500, "repeats": 10, "od_pairs": 20},
    "beijing": {"samples": 500, "repeats": 10, "od_pairs": 20},
}


def generate_data(nodes: int, edges: int, samples: int, repeats: int,
                  od_pairs_count: int, seed: int, output_dir: Path,
                  preset: str | None = None):
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating data: {nodes} nodes, {edges} edges, N={samples}, "
          f"repeats={repeats}, OD={od_pairs_count}, seed={seed}")
    print(f"Output: {output_dir}")

    # Network
    if preset == "beijing":
        print("  Loading Beijing OSM road network...")
        network = load_beijing_network()
        print(f"  Loaded: {network.num_nodes} nodes, {network.num_edges} edges")
    else:
        network = create_artificial_network(nodes, edges, seed=seed)
    network.save(output_dir / "network.npz")
    print(f"  network.npz: {network.num_nodes} nodes, {network.num_edges} edges")

    # OD pairs
    od = random_od_pairs(network, od_pairs_count, seed=seed)
    np.save(output_dir / "od_pairs.npy", np.array(od, dtype=np.int32))
    print(f"  od_pairs.npy: {len(od)} pairs")

    # Travel times (one matrix per repeat)
    tt_data = {}
    for r in range(repeats):
        if preset == "beijing":
            W = generate_beijing_travel_times(network, samples, seed=1000 + r)
        else:
            W = generate_travel_times(network.num_edges, samples, (10.0, 100.0), seed=1000 + r)
        tt_data[f"repeat_{r:02d}"] = W
    np.savez(output_dir / "travel_times.npz", **tt_data)
    print(f"  travel_times.npz: {repeats} repeats x ({samples}, {network.num_edges})")

    # Meta
    meta = {
        "num_nodes": network.num_nodes,
        "num_edges": network.num_edges,
        "num_samples": samples,
        "num_repeats": repeats,
        "num_od_pairs": od_pairs_count,
        "seed": seed,
    }
    if preset == "beijing":
        meta["network_source"] = "OpenStreetMap (offline GraphML extracted from PBF)"
        meta["location"] = "Beijing, China"
        meta["travel_time_model"] = "lognormal, attribute-driven (length/speed + road-type CV)"
        meta["highway_cv_range"] = {
            highway: [cv_lo, cv_hi]
            for highway, (cv_lo, cv_hi) in sorted(HIGHWAY_CV_RANGE.items())
        }
    else:
        meta["travel_time_range"] = [10.0, 100.0]
        meta["travel_time_std_ratio"] = [0.5, 1.2]
    with open(output_dir / "meta.yaml", "w") as f:
        yaml.dump(meta, f, default_flow_style=False)
    print(f"  meta.yaml: saved")
    print("Done!")


def main():
    parser = argparse.ArgumentParser(description="Generate experiment data")
    parser.add_argument("--preset", choices=["small", "full", "beijing"], help="Use preset parameters")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for graph generation")
    parser.add_argument("--nodes", type=int, help="Number of nodes")
    parser.add_argument("--edges", type=int, help="Number of edges")
    parser.add_argument("--samples", type=int, help="Number of travel time samples (N)")
    parser.add_argument("--repeats", type=int, help="Number of repeats")
    parser.add_argument("--od-pairs", type=int, help="Number of OD pairs")
    parser.add_argument("--output", type=str, help="Output directory (overrides default)")
    args = parser.parse_args()

    if args.preset:
        params = PRESETS[args.preset].copy()
    else:
        params = {
            "nodes": args.nodes or 65,
            "edges": args.edges or 123,
            "samples": args.samples or 500,
            "repeats": args.repeats or 10,
            "od_pairs": args.od_pairs or 20,
        }

    seed = args.seed

    if args.output:
        output_dir = Path(__file__).parent / args.output
    elif args.preset == "small":
        output_dir = Path(__file__).parent / "small"
    elif args.preset == "full":
        output_dir = Path(__file__).parent / f"full/seed{seed}"
    elif args.preset == "beijing":
        output_dir = Path(__file__).parent / "beijing"
    else:
        output_dir = Path(__file__).parent / f"full/seed{seed}"

    # For beijing, nodes/edges come from OSM
    if args.preset == "beijing":
        nodes, edges = 0, 0  # placeholder, OSM determines actual size
    else:
        nodes = params["nodes"]
        edges = params["edges"]

    generate_data(
        nodes=nodes,
        edges=edges,
        samples=params["samples"],
        repeats=params["repeats"],
        od_pairs_count=params["od_pairs"],
        seed=seed,
        output_dir=output_dir,
        preset=args.preset,
    )


if __name__ == "__main__":
    main()
