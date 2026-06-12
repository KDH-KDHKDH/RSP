"""Tests for the root-level public SDK facade."""

from pathlib import Path
import sys

import networkx as nx
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from Cao_SOTA_MP.src.graph import RoadNetwork
from Cao_SOTA_MP.src import experiment as experiment_mod
from rsp import RSPConfig, RSPDataset, RSPResult, RSPRunner, RSPTimeDependentDataset


def make_sdk_network() -> RoadNetwork:
    graph = nx.DiGraph()
    graph.add_edges_from([(0, 1), (1, 2), (0, 2)])
    return RoadNetwork.from_networkx(graph)


def test_public_sdk_imports_are_available():
    assert RSPDataset is not None
    assert RSPTimeDependentDataset is not None
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


def test_time_dependent_dataset_from_arrays_accepts_3d_and_4d_tensors():
    network = make_sdk_network()
    td = np.ones((2, 4, network.num_edges), dtype=np.float64)
    dataset = RSPTimeDependentDataset.from_arrays(
        network=network,
        travel_times=td,
        od_pairs=[(0, 2)],
        time_step=0.5,
    )

    assert dataset.num_repeats == 1
    assert dataset.num_samples == 2
    assert dataset.num_time_steps == 4
    assert dataset.time_step == 0.5
    assert dataset.travel_times[0].shape == (2, 4, network.num_edges)

    repeated = RSPTimeDependentDataset.from_arrays(
        network=network,
        travel_times=np.stack([td, td * 2.0]),
        od_pairs=[(0, 2)],
    )

    assert repeated.num_repeats == 2
    assert repeated.travel_times[1][0, 0, 0] == 2.0


def test_time_dependent_dataset_from_cao_dataset_scales_by_time_profile():
    network = make_sdk_network()
    W = np.array(
        [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
        ]
    )
    cao_dataset = RSPDataset.from_arrays(
        network=network,
        travel_times=W,
        od_pairs=[(0, 2)],
        meta={"name": "cao-to-yang"},
    )
    profile = np.array([1.0, 1.5, 2.0])

    td_dataset = RSPTimeDependentDataset.from_cao_dataset(
        cao_dataset,
        time_profile=profile,
        time_step=1.0,
        auto_horizon=False,
    )

    expected = W[:, None, :] * profile[None, :, None]
    assert np.allclose(td_dataset.travel_times[0], expected)
    assert td_dataset.edge_order == cao_dataset.edge_order
    assert td_dataset.meta["name"] == "cao-to-yang"
    assert td_dataset.deadline_matrix().shape == W.shape
    assert np.allclose(td_dataset.deadline_matrix(), expected.mean(axis=1))


def test_time_dependent_dataset_from_cao_dataset_auto_extends_horizon():
    network = make_sdk_network()
    W = np.array(
        [
            [1.0, 10.0, 1.0],
            [1.0, 12.0, 1.0],
        ],
        dtype=np.float64,
    )
    cao_dataset = RSPDataset.from_arrays(
        network=network,
        travel_times=W,
        od_pairs=[(0, 2)],
    )

    td_dataset = RSPTimeDependentDataset.from_cao_dataset(
        cao_dataset,
        time_profile=[1.0],
        time_step=1.0,
    )

    assert td_dataset.num_time_steps == 2
    assert td_dataset.meta["auto_horizon"] is True
    assert td_dataset.meta["input_time_profile_length"] == 1
    assert td_dataset.meta["time_profile_length"] == 2
    assert td_dataset.meta["auto_horizon_added_steps"] == 1
    assert np.allclose(td_dataset.travel_times[0][:, :, 0], 1.0)
    assert np.allclose(td_dataset.travel_times[0][:, :, 2], 1.0)


def test_time_dependent_dataset_from_networkx_generates_from_edge_attributes():
    graph = nx.DiGraph()
    graph.add_edge(0, 1, mean_time=10.0, cv=0.2)
    graph.add_edge(1, 2, mean_time=20.0, sigma=0.3)
    graph.add_edge(0, 2, mean_time=25.0, cv=0.1)
    profile = np.array([1.0, 1.2])

    dataset = RSPTimeDependentDataset.from_networkx(
        graph=graph,
        od_pairs=[(0, 2)],
        time_profile=profile,
        num_samples=5,
        random_seed=123,
    )

    assert dataset.travel_times[0].shape == (5, 2, graph.number_of_edges())
    assert np.all(dataset.travel_times[0] > 0)
    assert dataset.edge_order == list(graph.edges())
    assert dataset.meta["source"] == "edge_attributes"
    assert dataset.deadline_matrix().shape == (5, graph.number_of_edges())


def test_time_dependent_dataset_rejects_invalid_inputs():
    network = make_sdk_network()

    with pytest.raises(ValueError, match="must be 3D"):
        RSPTimeDependentDataset.from_arrays(
            network=network,
            travel_times=np.ones((4, network.num_edges)),
            od_pairs=[(0, 2)],
        )

    with pytest.raises(ValueError, match="expected .* network edges"):
        RSPTimeDependentDataset.from_arrays(
            network=network,
            travel_times=np.ones((2, 3, network.num_edges + 1)),
            od_pairs=[(0, 2)],
        )

    with pytest.raises(ValueError, match="time_profile must contain positive"):
        RSPTimeDependentDataset.lift_cao_samples_to_time_dependent(
            np.ones((2, network.num_edges)),
            [1.0, 0.0],
        )

    graph = nx.DiGraph()
    graph.add_edge(0, 1, mean_time=10.0, cv=0.2)
    graph.add_edge(1, 2, mean_time=20.0)
    with pytest.raises(ValueError, match="must define sigma or cv"):
        RSPTimeDependentDataset.from_networkx(
            graph=graph,
            od_pairs=[(0, 2)],
            time_profile=[1.0, 1.1],
            num_samples=3,
        )


def test_time_dependent_dataset_rejects_invalid_probabilities_and_od():
    network = make_sdk_network()
    td = np.ones((2, 3, network.num_edges), dtype=np.float64)

    with pytest.raises(ValueError, match="sample_probabilities length"):
        RSPTimeDependentDataset.from_arrays(
            network=network,
            travel_times=td,
            od_pairs=[(0, 2)],
            sample_probabilities=np.array([1 / 3, 1 / 3, 1 / 3]),
        )

    with pytest.raises(ValueError, match="sum to 1"):
        RSPTimeDependentDataset.from_arrays(
            network=network,
            travel_times=td,
            od_pairs=[(0, 2)],
            sample_probabilities=np.array([0.4, 0.4]),
        )

    with pytest.raises(ValueError, match="outside network"):
        RSPTimeDependentDataset.from_arrays(
            network=network,
            travel_times=td,
            od_pairs=[(0, 99)],
        )


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


def test_config_accepts_yang_otap_method():
    config = RSPConfig(methods=("Yang_OTAP_ILP",), alphas=(0.5,))

    assert config.methods == ("Yang_OTAP_ILP",)


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


def test_runner_solve_case_supports_yang_time_dependent_dataset():
    network = make_sdk_network()
    W = np.array(
        [
            [1.0, 1.0, 3.0],
            [2.0, 2.0, 3.0],
            [6.0, 6.0, 3.0],
        ],
        dtype=np.float64,
    )
    cao_dataset = RSPDataset.from_arrays(
        network=network,
        travel_times=W,
        od_pairs=[(0, 2)],
    )
    dataset = RSPTimeDependentDataset.from_cao_dataset(
        cao_dataset,
        time_profile=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        time_step=1.0,
    )
    config = RSPConfig(
        methods=("Yang_OTAP_ILP",),
        alphas=(0.5,),
        solver_backend="CBC",
        deadline_mode="exact",
        deadline_enumeration_cutoff=3,
        time_limit=10,
    )

    case = RSPRunner(dataset, config).solve_case(repeat=0, od_idx=0, alpha=0.5)

    yang = case.metrics["methods"]["Yang_OTAP_ILP"]
    assert case.tau == pytest.approx(3.5)
    assert case.ilp is None
    assert yang["status"] == "Optimal"
    assert yang["punctuality_prob"] is not None
    assert yang["lateness_count"] + yang["on_time_count"] == dataset.num_samples
    assert yang["path_edges"]
    assert yang["sample_travel_times"].shape == (dataset.num_samples,)
    assert yang["arrival_time_indices"].shape == (dataset.num_samples,)
    assert "Yang_OTAP_ILP found path" in yang["conclusion"]


def test_runner_run_returns_yang_dataframe_and_summary():
    network = make_sdk_network()
    W = np.array(
        [
            [1.0, 1.0, 3.0],
            [2.0, 2.0, 3.0],
            [6.0, 6.0, 3.0],
        ],
        dtype=np.float64,
    )
    dataset = RSPTimeDependentDataset.from_cao_dataset(
        RSPDataset.from_arrays(
            network=network,
            travel_times=W,
            od_pairs=[(0, 2)],
            meta={"name": "td-toy"},
        ),
        time_profile=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    )
    config = RSPConfig(
        methods=("Yang_OTAP_ILP",),
        alphas=(0.5,),
        num_repeats=1,
        num_od_pairs=1,
        solver_backend="CBC",
        deadline_mode="exact",
        deadline_enumeration_cutoff=3,
        time_limit=10,
    )

    result = RSPRunner(dataset, config).run(progress=False)
    df = result.to_dataframe()

    assert len(df) == 1
    assert df.loc[0, "method"] == "Yang_OTAP_ILP"
    assert df.loc[0, "status"] == "Optimal"
    assert df.loc[0, "on_time_count"] + df.loc[0, "lateness_count"] == dataset.num_samples
    assert df.loc[0, "path_length"] >= 1
    assert isinstance(df.loc[0, "path_edges"], list)
    assert isinstance(df.loc[0, "conclusion"], str)
    assert result.dataset_meta["name"] == "td-toy"

    summary = result.summary()
    assert summary.loc[0, "method"] == "Yang_OTAP_ILP"
    assert "mean_on_time_count" in summary.columns
    assert "mean_lateness_count" in summary.columns
    assert summary.loc[0, "optimal_rate"] == 1.0


def test_runner_rejects_yang_method_for_static_dataset():
    dataset = RSPDataset.from_arrays(
        network=make_sdk_network(),
        travel_times=np.ones((3, 3), dtype=np.float64),
        od_pairs=[(0, 2)],
    )
    runner = RSPRunner(
        dataset,
        RSPConfig(
            methods=("Yang_OTAP_ILP",),
            alphas=(0.5,),
            solver_backend="CBC",
            deadline_mode="exact",
            deadline_enumeration_cutoff=3,
        ),
    )

    with pytest.raises(ValueError, match="requires RSPTimeDependentDataset"):
        runner.solve_case(repeat=0, od_idx=0, alpha=0.5)


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
