"""Run with python -m helion_pipeline --help from the repository checkout."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import sys
import traceback

from .common import ROOT, digest, load_config, write_json

STAGES = ("validate", "train", "score", "replay", "schedule", "report")
PREREQUISITES = {"validate": [], "train": ["validate"], "score": ["train"],
                 "replay": ["score"], "schedule": [], "report": ["score", "replay", "schedule"]}


def source_checksums(root):
    files = []
    for directory in ("data", "metadata", "project/brief", "project/design", "project/evidence", "synthetic-data-assumptions"):
        files.extend(p for p in (root / directory).rglob("*") if p.is_file())
    files.extend(p for p in (root / "project/presentation").glob("*.md"))
    return {str(p.relative_to(root)): digest(p) for p in sorted(files)}


def initialise_manifest(root, out, config):
    path = out / "run_manifest.json"
    checksums = source_checksums(root)
    if path.exists():
        manifest = json.loads(path.read_text())
        if manifest["config"] != config:
            raise ValueError("Run configuration changed; use a new output directory")
        if manifest["source_checksums"] != checksums:
            raise ValueError("Source files changed; use a new output directory after reviewing the change")
        return manifest
    packages = {}
    for name in ("numpy", "pandas", "scikit-learn", "scipy", "joblib", "pyarrow", "matplotlib", "nbformat", "pytest"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "unavailable"
    manifest = {"version": "HELION-PIPELINE-002", "created_utc": datetime.now(timezone.utc).isoformat(),
                "config": config, "source_checksums": checksums, "python": sys.version,
                "dependencies": packages, "stages": {}, "source_kind": "synthetic",
                "production_qualified": False, "test_interpretation": "retrospective_not_pristine_holdout"}
    write_json(path, manifest)
    write_json(out / "config_used.json", config)
    ops = json.loads((root / config["operating_assumptions"]).read_text())
    write_json(out / "operating_assumptions_used.json", ops)
    (out / "requirements.lock.txt").write_text("\n".join(f"{k}=={v}" for k, v in packages.items() if v != "unavailable") + "\n")
    return manifest


def execute(stage, root, out, config):
    if stage == "validate":
        from .data import validate_and_prepare
        return validate_and_prepare(root, out, config)
    if stage == "train":
        from .model import train_models
        return train_models(root, out, config)
    if stage == "score":
        from .model import score_models
        return score_models(root, out, config)
    if stage == "replay":
        from .replay import run_replay
        return run_replay(root, out, config)
    if stage == "schedule":
        from .scheduling import run_scheduling
        return run_scheduling(root, out, config)
    if stage == "report":
        from .reporting import build_report
        return build_report(root, out, config)
    raise ValueError(stage)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Helion offline synthetic model and diagnostic-selection research")
    parser.add_argument("stage", choices=["run", *STAGES])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/helion_pipeline/research_v2_concern_closure",
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--replications", type=int, help="Override for a smoke run in a separate output directory")
    parser.add_argument("--bootstrap-samples", type=int, help="Override for a smoke run in a separate output directory")
    args = parser.parse_args(argv)
    config = load_config(args.config)
    for key in ("replications", "bootstrap_samples"):
        value = getattr(args, key)
        if value is not None:
            if value < 1:
                parser.error(f"{key} must be positive")
            config[key] = value
    root, out = args.root.resolve(), args.out.resolve()
    # Never permit a derived-output destination inside authoritative input folders.
    protected = [root / p for p in ("data", "metadata", "project", "synthetic-data-assumptions")]
    if out == root or any(out == p or p in out.parents for p in protected):
        parser.error("Output must be an isolated derived-artifact directory")
    out.mkdir(parents=True, exist_ok=True)
    manifest = initialise_manifest(root, out, config)
    stages = STAGES if args.stage == "run" else [args.stage]
    for stage in stages:
        for prerequisite in PREREQUISITES[stage]:
            if manifest["stages"].get(prerequisite, {}).get("status") != "complete":
                raise ValueError(f"{stage} requires a successful {prerequisite} stage in this run")
        stage_code = {str(p.relative_to(root)): digest(p) for p in sorted((root / "helion_pipeline").glob("*.py"))}
        manifest["stages"][stage] = {"status": "running", "code_checksums": stage_code}
        # Invalidate later dependent results rather than treating stale scores as fresh.
        for later in STAGES[STAGES.index(stage) + 1:]:
            if stage in {"validate", "train", "score", "replay"} or later == "report":
                if later in manifest["stages"]:
                    manifest["stages"][later]["status"] = "stale"
        write_json(out / "run_manifest.json", manifest)
        print(f"Starting {stage}", flush=True)
        try:
            result = execute(stage, root, out, config)
        except Exception as exc:
            manifest["stages"][stage] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}", "code_checksums": stage_code}
            write_json(out / "run_manifest.json", manifest)
            raise
        manifest["stages"][stage] = {"status": "complete", "code_checksums": stage_code}
        manifest["code_checksums"] = {str(p.relative_to(root)): digest(p) for p in sorted((root / "helion_pipeline").glob("*.py"))}
        write_json(out / "run_manifest.json", manifest)
        print(f"Completed {stage}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
