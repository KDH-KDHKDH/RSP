"""Data generation script for the punctuality problem experiments.

Generates network topology, travel time samples, and OD pairs,
saving them to disk for later use by the experiment runner.

Usage:
    # Presets
    uv run python Cao_SOTA_MP/data/generate.py --preset small
    uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 42
    uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 99
    uv run python Cao_SOTA_MP/data/generate.py --preset full --seed 200

    # Custom
    uv run python Cao_SOTA_MP/data/generate.py --nodes 65 --edges 123 --samples 500 --repeats 10 --od-pairs 20 --seed 42 --output data/full/seed42
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.generator import create_artificial_network, generate_travel_times, random_od_pairs


PRESETS = {
    "small": {"nodes": 10, "edges": 20, "samples": 50, "repeats": 3, "od_pairs": 5},
    "full": {"nodes": 65, "edges": 123, "samples": 500, "repeats": 10, "od_pairs": 20},
}


def generate_data(nodes: int, edges: int, samples: int, repeats: int,
                  od_pairs_count: int, seed: int, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating data: {nodes} nodes, {edges} edges, N={samples}, "
          f"repeats={repeats}, OD={od_pairs_count}, seed={seed}")
    print(f"Output: {output_dir}")

    # Network
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
        W = generate_travel_times(network.num_edges, samples, (10.0, 100.0), seed=1000 + r)
        tt_data[f"repeat_{r:02d}"] = W
    np.savez(output_dir / "travel_times.npz", **tt_data)
    print(f"  travel_times.npz: {repeats} repeats x ({samples}, {network.num_edges})")

    # Meta
    meta = {
        "num_nodes": nodes,
        "num_edges": edges,
        "num_samples": samples,
        "num_repeats": repeats,
        "num_od_pairs": od_pairs_count,
        "seed": seed,
        "travel_time_range": [10.0, 100.0],
        "travel_time_std_ratio": [0.5, 1.2],
    }
    with open(output_dir / "meta.yaml", "w") as f:
        yaml.dump(meta, f, default_flow_style=False)
    print(f"  meta.yaml: saved")
    print("Done!")


def main():
    parser = argparse.ArgumentParser(description="Generate experiment data")
    parser.add_argument("--preset", choices=["small", "full"], help="Use preset parameters")
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
    else:
        output_dir = Path(__file__).parent / f"full/seed{seed}"

    generate_data(
        nodes=params["nodes"],
        edges=params["edges"],
        samples=params["samples"],
        repeats=params["repeats"],
        od_pairs_count=params["od_pairs"],
        seed=seed,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
