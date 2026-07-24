"""TrustMesh-Bench — one entrypoint for the whole evaluation suite.

TrustMesh-Bench is the named, public-facing evaluation artifact for the trust
engine. Rather than remembering four separate scripts, run one command:

    python scripts/run_trustmesh_bench.py all              # full suite
    python scripts/run_trustmesh_bench.py holdout --limit 8
    python scripts/run_trustmesh_bench.py calibration
    python scripts/run_trustmesh_bench.py all --dry-run    # show what would run

Each sub-benchmark is an existing, CI-wired runner; this dispatcher just gives
them a single front door and a consistent flag surface. See
docs/TRUSTMESH_BENCH.md for what each one measures and how results are recorded.

The underlying runners call a live LLM and abort cleanly if no real API key is
configured (mock mode). Use --dry-run to inspect the resolved commands without
running anything (no key required).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent

# Each benchmark maps to its script and the passthrough flags it understands.
# Keeping this table explicit (rather than forwarding every flag blindly) means
# we never hand a runner an option it does not accept.
_BENCHMARKS: dict[str, dict] = {
    "holdout": {
        "script": "run_manipulation_holdout.py",
        "supports": {"limit", "no_cache", "holdout_thresholds"},
        "desc": "ManipulationDetector adversarial holdout (CI-gated precision/recall).",
    },
    "negotiation": {
        "script": "run_benchmark.py",
        "supports": {"limit", "no_cache"},
        "desc": "Primary negotiation benchmark across policy + commitment detectors.",
    },
    "adversarial": {
        "script": "run_adversarial_benchmark.py",
        "supports": {"limit", "no_cache"},
        "desc": "Adversarial scenarios testing prompt-injection resistance.",
    },
    "calibration": {
        "script": "compute_calibration_metrics.py",
        "supports": {"limit"},
        "desc": "Brier score + Expected Calibration Error for the detector.",
    },
}

# The order the full suite runs in.
_ALL_ORDER = ["holdout", "negotiation", "adversarial", "calibration"]


def resolve_commands(args: argparse.Namespace) -> list[list[str]]:
    """Pure command resolution — returns the argv list for each benchmark to run.

    Kept side-effect-free so it can be unit-tested without invoking anything.
    """
    if args.benchmark == "all":
        names = list(_ALL_ORDER)
    else:
        names = [args.benchmark]

    commands: list[list[str]] = []
    for name in names:
        spec = _BENCHMARKS[name]
        cmd = [sys.executable, str(_SCRIPTS_DIR / spec["script"])]
        supports = spec["supports"]
        if args.limit is not None and "limit" in supports:
            cmd += ["--limit", str(args.limit)]
        if args.no_cache and "no_cache" in supports:
            cmd.append("--no-cache")
        if "holdout_thresholds" in supports:
            if args.fail_below_precision is not None:
                cmd += ["--fail-below-precision", str(args.fail_below_precision)]
            if args.fail_below_recall is not None:
                cmd += ["--fail-below-recall", str(args.fail_below_recall)]
            if args.prompt_version is not None:
                cmd += ["--prompt-version", args.prompt_version]
        commands.append(cmd)
    return commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_trustmesh_bench.py",
        description="TrustMesh-Bench — unified evaluation suite entrypoint.",
    )
    choices = list(_BENCHMARKS) + ["all"]
    parser.add_argument(
        "benchmark",
        choices=choices,
        help="Which benchmark to run: " + ", ".join(choices),
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of scenarios")
    parser.add_argument("--no-cache", action="store_true", help="Disable LLM response caching")
    parser.add_argument("--fail-below-precision", type=float, default=None,
                        help="(holdout) fail if precision drops below this")
    parser.add_argument("--fail-below-recall", type=float, default=None,
                        help="(holdout) fail if recall drops below this")
    parser.add_argument("--prompt-version", type=str, default=None,
                        help="(holdout) note the prompt version used")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the commands that would run, then exit (no LLM, no key needed)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    commands = resolve_commands(args)

    if args.dry_run:
        for name, cmd in zip(_ALL_ORDER if args.benchmark == "all" else [args.benchmark], commands):
            print(f"[{name}] {' '.join(cmd)}")
        return 0

    overall_rc = 0
    for cmd in commands:
        print(f"\n=== running: {' '.join(cmd)} ===", flush=True)
        rc = subprocess.call(cmd, cwd=str(_SCRIPTS_DIR.parent))
        if rc != 0:
            overall_rc = rc
            print(f"--- benchmark exited with code {rc} ---", flush=True)
    return overall_rc


if __name__ == "__main__":
    raise SystemExit(main())
