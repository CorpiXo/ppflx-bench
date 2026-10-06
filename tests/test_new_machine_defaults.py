"""Defaults a new machine relies on: the full mode set, the dataset folder, and
key error messages that point at a local setup, never at re-keying."""

import importlib.util
import inspect
import tomllib
from pathlib import Path

import pytest

import compare
import download_datasets
from ppflx_bench.compare import experiment, runner
from ppflx_bench.compare.registry import DEFAULT_DATA_PATH, MODES

REPO = Path(__file__).resolve().parents[1]


def test_compare_defaults_to_every_registered_mode(monkeypatch):
    seen = {}

    def fake_run_comparison(**kwargs):
        seen.update(kwargs)
        return []

    monkeypatch.setattr(runner, "run_comparison", fake_run_comparison)
    assert compare.main(["--dataset", "healthcare"]) == 0
    assert seen["modes"] is None
    # The published configuration: 3 clients, 10 rounds.
    assert (seen["num_clients"], seen["num_rounds"]) == (3, 10)
    assert (runner.CompareConfig().num_clients, runner.CompareConfig().num_rounds) == (3, 10)
    cfg = runner._merge_dataset_defaults(runner.CompareConfig(dataset="healthcare", modes=seen["modes"]))
    assert cfg.modes == list(MODES)
    assert {"he_elgamal_zkp", "he_elgamal_zkp_sampled"} <= set(cfg.modes)


def test_run_comparison_script_all_is_the_registry():
    spec = importlib.util.spec_from_file_location("run_comparison_script", REPO / "scripts" / "run_comparison.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.ALL_MODES == list(MODES)


def test_default_data_path_is_the_folder_download_datasets_fills():
    assert DEFAULT_DATA_PATH == "./dataset/"
    assert compare._build_parser().parse_args([]).data_path == DEFAULT_DATA_PATH
    assert runner.CompareConfig().data_path == DEFAULT_DATA_PATH
    for fn in (runner.run_comparison, runner.run_alpha_sweep, runner.run_dp_epsilon_sweep):
        assert inspect.signature(fn).parameters["data_path"].default == DEFAULT_DATA_PATH
    flower_config = tomllib.loads((REPO / "pyproject.toml").read_text())["tool"]["flwr"]["app"]["config"]
    assert flower_config["data-path"] == DEFAULT_DATA_PATH
    assert download_datasets.DATASET_DIR == (REPO / DEFAULT_DATA_PATH).resolve()


def _assert_local_setup_hint(out: str) -> None:
    assert "--force" not in out
    assert "commit the" not in out.lower() and "re-pin" not in out.lower()
    assert "zkp_gnark_service" not in out
    assert "setup --keys-dir ~/.cache/ppflx/keys --pk-dir ~/.cache/ppflx/pk" in out
    assert "FL_ZKP_KEYS_DIR" in out and "FL_ZKP_PK_DIR" in out


def test_missing_proving_keys_message_gives_the_local_setup(monkeypatch, capsys):
    import ppflx.core.gnark_keys as gnark_keys

    monkeypatch.setattr(gnark_keys, "load_manifest", lambda: {})
    monkeypatch.setattr(gnark_keys, "missing_proving_keys", lambda: ["norm-256.pk"])
    monkeypatch.setattr(experiment, "_gnark_binary", lambda: pytest.fail("started without proving keys"))
    assert experiment._ensure_gnark_service("unused") is False
    out = capsys.readouterr().out
    assert "norm-256.pk" in out
    _assert_local_setup_hint(out)


def test_missing_manifest_message_gives_the_local_setup(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("FL_ZKP_KEYS_DIR", str(tmp_path / "empty"))
    assert experiment._ensure_gnark_service("unused") is False
    _assert_local_setup_hint(capsys.readouterr().out)


def test_proof_service_binary_is_required(monkeypatch, capsys):
    monkeypatch.delenv("FL_GNARK_BINARY", raising=False)
    assert experiment._gnark_binary() is None
    out = capsys.readouterr().out
    assert "FL_GNARK_BINARY" in out and "gnark-gradient-prover" in out


def test_networked_run_budget_scales_with_rounds(monkeypatch):
    monkeypatch.delenv("FL_SERVER_TIMEOUT", raising=False)
    monkeypatch.delenv("FL_CLIENT_TIMEOUT", raising=False)
    elgamal, baseline = MODES["he_elgamal_zkp"], MODES["baseline"]
    # he_elgamal_zkp on creditcard takes about 21 min a round: 20 rounds must fit.
    assert experiment._run_timeout(elgamal, False, 20) >= 20 * 21 * 60 + 1800
    # Short runs keep the previous floors.
    assert experiment._run_timeout(elgamal, False, 2) == 21600 + 1800
    assert experiment._run_timeout(baseline, False, 20) == 7200 + 1800
    # MNIST ElGamal took about 3.3 h a round (352 proofs per client): 20 rounds must fit.
    assert experiment._run_timeout(elgamal, False, 20, "mnist") >= 20 * 3.3 * 3600 + 1800
    assert experiment._run_timeout(MODES["he_elgamal_zkp_sampled"], False, 20, "cifar") > 20 * 3.3 * 3600
    # The per-dataset budget is for the ElGamal modes only.
    assert experiment._run_timeout(MODES["zkp"], False, 20, "mnist") == 20 * 1800 + 1800
    monkeypatch.setenv("FL_CLIENT_TIMEOUT", "100")
    assert experiment._run_timeout(elgamal, False, 20) == 100 + 1800
    monkeypatch.setenv("FL_SERVER_TIMEOUT", "50")
    assert experiment._run_timeout(elgamal, False, 20) == 50


def test_every_client_evaluates_every_round(tmp_path):
    from ppflx_bench.compare.experiment import run_config_for

    run_config = run_config_for("baseline", {"number_clients": 3}, str(tmp_path), simulation=False)
    assert run_config["frac-eval"] == 1.0 and run_config["min-eval-clients"] == 3
    assert tomllib.loads((REPO / "pyproject.toml").read_text())["tool"]["flwr"]["app"]["config"]["frac-eval"] == 1.0
