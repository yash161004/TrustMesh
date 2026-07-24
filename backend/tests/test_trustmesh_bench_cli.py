"""Tests for the TrustMesh-Bench unified dispatcher (offline — no LLM/key)."""
import importlib.util
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "run_trustmesh_bench.py"


@pytest.fixture(scope="module")
def bench():
    spec = importlib.util.spec_from_file_location("run_trustmesh_bench", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve(bench, argv):
    args = bench.build_parser().parse_args(argv)
    return bench.resolve_commands(args)


def test_all_runs_every_benchmark_in_order(bench):
    cmds = _resolve(bench, ["all"])
    scripts = [Path(c[1]).name for c in cmds]
    assert scripts == [
        "run_manipulation_holdout.py",
        "run_benchmark.py",
        "run_adversarial_benchmark.py",
        "compute_calibration_metrics.py",
    ]


def test_limit_passes_through_where_supported(bench):
    (cmd,) = _resolve(bench, ["holdout", "--limit", "8"])
    assert "--limit" in cmd and "8" in cmd


def test_no_cache_not_passed_to_calibration(bench):
    # calibration does not accept --no-cache; it must be filtered out.
    (cmd,) = _resolve(bench, ["calibration", "--no-cache", "--limit", "3"])
    assert "--no-cache" not in cmd
    assert "--limit" in cmd and "3" in cmd


def test_no_cache_passed_to_holdout(bench):
    (cmd,) = _resolve(bench, ["holdout", "--no-cache"])
    assert "--no-cache" in cmd


def test_holdout_threshold_flags_pass_through(bench):
    (cmd,) = _resolve(bench, ["holdout", "--fail-below-precision", "0.95",
                              "--fail-below-recall", "0.9", "--prompt-version", "v2"])
    assert "--fail-below-precision" in cmd and "0.95" in cmd
    assert "--fail-below-recall" in cmd and "0.9" in cmd
    assert "--prompt-version" in cmd and "v2" in cmd


def test_threshold_flags_not_applied_to_negotiation(bench):
    (cmd,) = _resolve(bench, ["negotiation", "--fail-below-precision", "0.95"])
    assert "--fail-below-precision" not in cmd


def test_no_optional_flags_when_unset(bench):
    (cmd,) = _resolve(bench, ["negotiation"])
    # just the interpreter + script path
    assert len(cmd) == 2
    assert Path(cmd[1]).name == "run_benchmark.py"


def test_dry_run_prints_and_exits_zero(bench, capsys):
    rc = bench.main(["all", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "[holdout]" in out and "[calibration]" in out
    # dry-run must not actually invoke anything (all four listed, none executed)
    assert out.count("run_manipulation_holdout.py") == 1


def test_invalid_benchmark_rejected(bench):
    with pytest.raises(SystemExit):
        bench.build_parser().parse_args(["nonexistent"])
