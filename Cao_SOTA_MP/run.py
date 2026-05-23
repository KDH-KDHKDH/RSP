"""One-click entry point for the punctuality problem reproduction."""

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from src.experiment import run_experiment
from src.visualize import plot_accuracy_vs_deadline, plot_probability_comparison, print_summary


def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Punctuality Problem Solver (Cao et al. 2020)")
    parser.add_argument("--config", default="configs/default.yaml", help="Config file path")
    parser.add_argument("--data-dir", default=None, help="Pre-generated data directory (overrides config)")
    parser.add_argument("--plot", action="store_true", help="Generate figures")
    parser.add_argument("--output", default=None, help="Output directory override")
    args = parser.parse_args()

    sys.stdout.reconfigure(line_buffering=True)

    config_path = Path(args.config)
    if not config_path.is_absolute():
        if not config_path.exists():
            config_path = Path(__file__).parent / args.config
    config = load_config(str(config_path))

    # Resolve data directory
    data_dir = args.data_dir or config.get("data", {}).get("dir")
    if data_dir and not Path(data_dir).is_absolute():
        # Try CWD first, then relative to script
        if Path(data_dir).exists():
            data_dir = str(Path(data_dir).resolve())
        else:
            data_dir = str(Path(__file__).parent / data_dir)

    # Resolve output directory
    output_dir = args.output or config.get("output", {}).get("dir", "results/")
    if not Path(output_dir).is_absolute():
        if Path(output_dir).exists():
            output_dir = str(Path(output_dir).resolve())
        else:
            output_dir = str(Path(__file__).parent / output_dir)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    fig_dir = str(Path(output_dir) / "figures")

    print(f"Config: {config_path}")
    print(f"Data:   {data_dir or '(inline generation)'}")
    print(f"Output: {output_dir}")

    # Run experiment
    print("\nRunning experiment...")
    df = run_experiment(config, data_dir=data_dir)

    # Print summary
    print_summary(df)

    # Save CSV
    if config.get("output", {}).get("save_csv", True):
        csv_path = f"{output_dir}/results.csv"
        df.to_csv(csv_path, index=False)
        print(f"Results saved to: {csv_path}")

    # Plot
    if args.plot or config.get("output", {}).get("save_figures", False):
        print("\nGenerating figures...")
        plot_accuracy_vs_deadline(df, fig_dir)
        plot_probability_comparison(df, fig_dir)

    print("\nDone!")


if __name__ == "__main__":
    main()
