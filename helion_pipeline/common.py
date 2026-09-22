"""Small shared I/O utilities; no feature or diagnostic business logic."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MECHANISMS = (
    "dram_electrical", "tsv_open_short", "microbump_open_bridge",
    "die_crack", "warpage", "underfill_void", "delamination",
)


def clean_json(value):
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_json(v) for v in value]
    if hasattr(value, "item"):
        return clean_json(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(clean_json(value), indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def load_config(path: Path | None = None):
    config = json.loads((path or Path(__file__).with_name("config.json")).read_text())
    if config["replications"] < 1 or config["bootstrap_samples"] < 1:
        raise ValueError("Replication and bootstrap counts must be positive")
    return config


def digest(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stable_uniform(*parts):
    payload = json.dumps(parts, separators=(",", ":")).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") / 2**64
