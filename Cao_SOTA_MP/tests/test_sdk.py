"""Tests for the root-level public SDK facade."""

from pathlib import Path
import sys

import networkx as nx
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from Cao_SOTA_MP.src.graph import RoadNetwork
from Cao_SOTA_MP.src import experiment as experiment_mod
from rsp import RSPConfig, RSPDataset, RSPResult, RSPRunner


def make_sdk_network() -> RoadNetwork:
    graph = nx.DiGraph()
    graph.add_edges_from([(0, 1), (1, 2), (0, 2)])
    return RoadNetwork.from_networkx(graph)


def test_public_sdk_imports_are_available():
    assert RSPDataset is not None
    assert RSPConfig is not None
    assert RSPRunner is not None


def test_dataset_from_directory_loads_small_data():
    dataset = RSPDataset.from_directory("Cao_SOTA_MP/data/small")

    assert dataset.network.num_edges > 0
    assert dataset.num_repeats > 0
    assert dataset.num_od_pairs > 0
    assert dataset.edge_order == dataset.network.edges
    assert dataset.travel_times[0].shape[1] == dataset.network.num_edges


def test_dataset_from_arrays_accepts_3d_travel_times():
    network = make_sdk_network()
    travel_times = np.ones((2, 4, network.num_edges))

    dataset = RSPDataset.from_arrays(
        network=network,
        travel_times=travel_times,
        od_pairs=[(0, 2)],
    )

    assert dataset.num_repeats == 2
    assert dataset.travel_times[0].shape == (4, network.num_edges)


def test_dataset_rejects_shape_mismatch():
    network = make_sdk_network()
    travel_times = np.ones((4, network.num_edges + 1))

    with pytest.raises(ValueError, match="expected .* network edges"):
        RSPDataset.from_arrays(
            network=network,
            travel_times=travel_times,
            od_pairs=[(0, 2)],
        )


def test_dataset_rejects_invalid_od_node():
    network = make_sdk_network()
    travel_times = np.ones((4, network.num_edges))

    with pytest.raises(ValueError, match="outside network"):
        RSPDataset.from_arrays(
            network=network,
            travel_times=travel_times,
            od_pairs=[(0, 99)],
        )


def test_dataset_from_networkx_freezes_edge_order():
    graph = nx.DiGraph()
    graph.add_edges_from([(0, 1), (1, 2), (0, 2)])
    edge_order = [(0, 2), (0, 1), (1, 2)]
    travel_times = np.ones((4, len(edge_order)))

    dataset = RSPDataset.from_networkx(
        graph=graph,
        travel_times=travel_times,
        od_pairs=[(0, 2)],
        edge_order=edge_order,
    )

    assert dataset.edge_order == edge_order
    assert dataset.network.edges == edge_order


def test_config_yaml_round_trip(tmp_path):
    config = RSPConfig(
        alphas=(0.5, 0.9),
        num_repeats=2,
        num_od_pairs=3,
        solver_backend="CBC",
        data_dir="Cao_SOTA_MP/data/small",
    )
    path = tmp_path / "config.yaml"

    config.to_yaml(path)
    loaded = RSPConfig.from_yaml(path)

    assert loaded.alphas == (0.5, 0.9)
    assert loaded.num_repeats == 2
    assert loaded.num_od_pairs == 3
    assert loaded.solver_backend == "CBC"
    assert loaded.data_dir == "Cao_SOTA_MP/data/small"
    assert loaded.expected_job_count == 12


def test_beijing_conflict_300_config_declares_report_21_scale():
    config = RSPConfig.from_yaml(Path("configs/beijing_conflict_300.yaml"))

    assert config.data_dir == "Cao_SOTA_MP/data/beijing_conflict"
    assert config.num_repeats == 3
    assert config.num_od_pairs == 20
    assert config.alphas == (0.5, 0.6, 0.7, 0.8, 0.9)
    assert config.solver_backend == "SCIP"
    assert config.deadline_mode == "heuristic"
    assert config.expected_job_count == 300


def test_runner_solve_case_returns_deadline_solver_results_and_metrics():
    network = make_sdk_network()
    W = np.array(
        [
            [1.0, 1.0, 3.0],
            [2.0, 2.0, 3.0],
            [6.0, 6.0, 3.0],
        ]
    )
    dataset = RSPDataset.from_arrays(
        network=network,
        travel_times=W,
        od_pairs=[(0, 2)],
    )
    config = RSPConfig(
        methods=("ILP", "MILP", "Dijkstra"),
        alphas=(0.5,),
        solver_backend="CBC",
        deadline_mode="exact",
        deadline_enumeration_cutoff=3,
        time_limit=10,
    )

    case = RSPRunner(dataset, config).solve_case(repeat=0, od_idx=0, alpha=0.5)

    assert case.tau == 3.5
    assert case.ilp["status"] == "Optimal"
    assert case.milp["status"] == "Optimal"
    assert case.dijkstra["status"] == "Optimal"
    assert case.ilp["punctuality_prob"] == pytest.approx(2 / 3)
    assert case.metrics["reference_available"] is True
    assert set(case.metrics["methods"]) == {"ILP", "MILP", "Dijkstra"}
    assert case.metrics["methods"]["ILP"]["correct"] is True
    assert case.metrics["methods"]["ILP"]["objective_gap"] == 0.0
    assert case.metrics["methods"]["ILP"]["tie_aware_correct"] is True
    assert case.metrics["methods"]["ILP"]["late_count"] == 1
    assert case.metrics["methods"]["ILP"]["path_length"] == 1
    assert case.metrics["deadline"]["mode"] == "exact"


def test_runner_solve_case_supports_origin_destination_without_od_idx():
    network = make_sdk_network()
    W = np.ones((3, network.num_edges))
    dataset = RSPDataset.from_arrays(
        network=network,
        travel_times=W,
        od_pairs=[(0, 2)],
    )
    config = RSPConfig(
        methods=("Dijkstra",),
        alphas=(0.5,),
        deadline_mode="exact",
        deadline_enumeration_cutoff=3,
    )

    case = RSPRunner(dataset, config).solve_case(
        repeat=0,
        origin=0,
        destination=2,
        alpha=0.5,
    )

    assert case.ilp is None
    assert case.dijkstra["status"] == "Optimal"
    assert case.metrics["od_idx"] is None
    assert case.metrics["reference_available"] is False
    assert case.metrics["methods"]["Dijkstra"]["correct"] is None


def test_runner_solve_case_rejects_invalid_repeat_and_od_args():
    dataset = RSPDataset.from_arrays(
        network=make_sdk_network(),
        travel_times=np.ones((3, 3)),
        od_pairs=[(0, 2)],
    )
    runner = RSPRunner(dataset, RSPConfig(alphas=(0.5,), deadline_mode="exact"))

    with pytest.raises(IndexError, match="repeat index"):
        runner.solve_case(repeat=1, od_idx=0, alpha=0.5)

    with pytest.raises(ValueError, match="Provide either od_idx"):
        runner.solve_case(repeat=0, alpha=0.5)

    with pytest.raises(ValueError, match="present in the dataset network"):
        runner.solve_case(repeat=0, origin=0, destination=99, alpha=0.5)

    with pytest.raises(ValueError, match="must be different"):
        runner.solve_case(repeat=0, origin=0, destination=0, alpha=0.5)


def test_runner_run_returns_result_dataframe_and_stays_quiet(capsys):
    network = make_sdk_network()
    W = np.array(
        [
            [1.0, 1.0, 3.0],
            [2.0, 2.0, 3.0],
            [6.0, 6.0, 3.0],
        ]
    )
    dataset = RSPDataset.from_arrays(
        network=network,
        travel_times=np.stack([W, W]),
        od_pairs=[(0, 2)],
        meta={"name": "toy"},
    )
    config = RSPConfig(
        methods=("ILP", "MILP", "Dijkstra"),
        alphas=(0.5,),
        num_repeats=1,
        num_od_pairs=1,
        solver_backend="CBC",
        deadline_mode="exact",
        deadline_enumeration_cutoff=3,
    )

    result = RSPRunner(dataset, config).run(progress=False)
    captured = capsys.readouterr()
    df = result.to_dataframe()

    assert captured.out == ""
    assert len(df) == 3
    assert set(df["method"]) == {"ILP", "MILP", "Dijkstra"}
    assert df["reference_available"].eq(True).all()
    assert df["tau"].eq(3.5).all()
    assert result.dataset_meta == {"name": "toy"}

    summary = result.summary()
    assert set(summary["method"]) == {"ILP", "MILP", "Dijkstra"}
    assert "tie_aware_accuracy" in summary.columns
    assert "mean_solve_time_s" in summary.columns


def test_runner_run_rejects_config_counts_beyond_dataset():
    dataset = RSPDataset.from_arrays(
        network=make_sdk_network(),
        travel_times=np.ones((3, 3)),
        od_pairs=[(0, 2)],
    )
    runner = RSPRunner(dataset, RSPConfig(num_repeats=2))

    with pytest.raises(ValueError, match="num_repeats=2 exceeds"):
        runner.run(progress=False)


def test_runner_run_matches_legacy_orchestration_core_metrics(tmp_path):
    network = make_sdk_network()
    W = np.array(
        [
            [1.0, 1.0, 3.0],
            [2.0, 2.0, 3.0],
            [6.0, 6.0, 3.0],
        ]
    )
    dataset = RSPDataset.from_arrays(
        network=network,
        travel_times=W,
        od_pairs=[(0, 2)],
    )
    config = RSPConfig(
        methods=("ILP", "MILP", "Dijkstra"),
        alphas=(0.5,),
        num_repeats=1,
        num_od_pairs=1,
        solver_backend="CBC",
        deadline_mode="exact",
        deadline_enumeration_cutoff=3,
    )

    data_dir = tmp_path / "toy"
    dataset.save(data_dir)
    sdk_df = RSPRunner(dataset, config).run(progress=False).to_dataframe()
    legacy_df = experiment_mod.run_experiment(
        {
            "experiment": {
                "num_repeats": 1,
                "num_od_pairs": 1,
                "alphas": [0.5],
            },
            "solver": {
                "backend": "CBC",
                "big_m": 1_000_000,
                "time_limit": 60,
            },
            "candidate_paths": {"max_paths": 1000},
            "deadline": {"mode": "exact", "enumeration_cutoff": 3},
        },
        data_dir=data_dir,
    )

    compare_cols = [
        "method",
        "repeat",
        "od_idx",
        "origin",
        "dest",
        "alpha",
        "punctuality_prob",
        "correct",
        "objective_gap",
        "tie_aware_correct",
        "late_count",
        "path_length",
        "reference_available",
        "reference_status",
    ]
    sdk_cmp = sdk_df[compare_cols].sort_values("method").reset_index(drop=True)
    legacy_cmp = legacy_df[compare_cols].sort_values("method").reset_index(drop=True)

    assert len(sdk_cmp) == len(legacy_cmp) == 3
    assert sdk_cmp.equals(legacy_cmp)


def test_result_helpers_return_stable_columns(tmp_path):
    dataset = RSPDataset.from_arrays(
        network=make_sdk_network(),
        travel_times=np.array(
            [
                [1.0, 1.0, 3.0],
                [2.0, 2.0, 3.0],
                [6.0, 6.0, 3.0],
            ]
        ),
        od_pairs=[(0, 2)],
    )
    config = RSPConfig(
        methods=("ILP", "MILP", "Dijkstra"),
        alphas=(0.5,),
        solver_backend="CBC",
        deadline_mode="exact",
        deadline_enumeration_cutoff=3,
    )
    result = RSPRunner(dataset, config).run(progress=False)

    solve_time = result.solve_time()
    assert {
        "method",
        "mean_solve_time_s",
        "median_solve_time_s",
        "max_solve_time_s",
        "min_solve_time_s",
    }.issubset(solve_time.columns)

    status_counts = result.status_counts()
    assert {"method", "status", "count", "rate"}.issubset(status_counts.columns)

    objective_gaps = result.objective_gaps()
    assert {
        "method",
        "mean_objective_gap",
        "median_objective_gap",
        "max_objective_gap",
        "min_objective_gap",
    }.issubset(objective_gaps.columns)

    by_alpha = result.by_alpha()
    assert {"alpha", "method", "tie_aware_accuracy"}.issubset(by_alpha.columns)

    by_od = result.by_od()
    assert {"od_idx", "method", "mean_punctuality_prob"}.issubset(by_od.columns)

    comparison = result.method_comparison()
    assert {
        "repeat",
        "od_idx",
        "alpha",
        "method",
        "reference",
        "method_punctuality_prob",
        "reference_punctuality_prob",
        "objective_gap",
        "tie_aware_correct",
        "path_match_correct",
        "method_status",
        "reference_status",
    }.issubset(comparison.columns)
    assert set(comparison["method"]) == {"MILP", "Dijkstra"}
    assert comparison["reference"].eq("ILP").all()

    figure_dir = tmp_path / "figures"
    result.save_figures(figure_dir)
    assert (figure_dir / "tie_aware_accuracy_vs_alpha.png").exists()


def test_runner_without_ilp_does_not_emit_reference_accuracy():
    dataset = RSPDataset.from_arrays(
        network=make_sdk_network(),
        travel_times=np.ones((3, 3)),
        od_pairs=[(0, 2)],
    )
    result = RSPRunner(
        dataset,
        RSPConfig(
            methods=("Dijkstra",),
            alphas=(0.5,),
            deadline_mode="exact",
            deadline_enumeration_cutoff=3,
        ),
    ).run(progress=False)

    df = result.to_dataframe()
    assert df["reference_available"].eq(False).all()
    assert df["correct"].isna().all()
    assert df["tie_aware_correct"].isna().all()
    assert df["objective_gap"].isna().all()


def test_result_method_comparison_requires_reference():
    df = RSPResult(
        df=RSPRunner(
            RSPDataset.from_arrays(
                network=make_sdk_network(),
                travel_times=np.ones((3, 3)),
                od_pairs=[(0, 2)],
            ),
            RSPConfig(
                methods=("Dijkstra",),
                alphas=(0.5,),
                deadline_mode="exact",
                deadline_enumeration_cutoff=3,
            ),
        )
        .run(progress=False)
        .to_dataframe()
    ).method_comparison()

    assert df.empty


def test_runner_run_matches_legacy_on_real_small_core_metrics():
    dataset = RSPDataset.from_directory("Cao_SOTA_MP/data/small")
    config = RSPConfig(
        methods=("ILP", "MILP", "Dijkstra"),
        alphas=(0.5,),
        num_repeats=1,
        num_od_pairs=1,
        solver_backend="CBC",
        deadline_mode="heuristic",
        max_candidate_paths=1000,
    )

    sdk_df = RSPRunner(dataset, config).run(progress=False).to_dataframe()
    legacy_df = experiment_mod.run_experiment(
        {
            "experiment": {
                "num_repeats": 1,
                "num_od_pairs": 1,
                "alphas": [0.5],
            },
            "solver": {
                "backend": "CBC",
                "big_m": 1_000_000,
                "time_limit": 60,
            },
            "candidate_paths": {"max_paths": 1000},
            "deadline": {"mode": "heuristic", "enumeration_cutoff": 15},
        },
        data_dir="Cao_SOTA_MP/data/small",
    )

    compare_cols = [
        "method",
        "repeat",
        "od_idx",
        "origin",
        "dest",
        "alpha",
        "punctuality_prob",
        "correct",
        "objective_gap",
        "tie_aware_correct",
        "late_count",
        "path_length",
        "reference_available",
        "reference_status",
    ]
    sdk_cmp = sdk_df[compare_cols].sort_values("method").reset_index(drop=True)
    legacy_cmp = legacy_df[compare_cols].sort_values("method").reset_index(drop=True)

    assert len(sdk_cmp) == len(legacy_cmp) == 3
    assert sdk_cmp.equals(legacy_cmp)
