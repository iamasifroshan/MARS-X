#!/usr/bin/env python3
"""Validate MARS-X dataset metadata against the JSON Schema.

Loads the dataset schema from data/metadata/dataset_schema.json and validates
every entry in the nasa_datasets JSON file. Exits with code 1 if any entry
fails validation.
"""

import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator, ValidationError
except ImportError:
    print("ERROR: jsonschema package not installed. Run: py -m pip install jsonschema")
    sys.exit(2)

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent  # E:\MARS-X
SCHEMA_PATH = ROOT / "data" / "metadata" / "dataset_schema.json"

# Try the backend copy first; fall back to the reference copy
BACKEND_DATASETS = ROOT / "backend" / "app" / "data" / "nasa_datasets.json"
REFERENCE_DATASETS = ROOT / "data" / "metadata" / "nasa_datasets_reference.json"


def load_json(path: Path) -> dict | list:
    """Load and return parsed JSON from *path*."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    # ── Load schema ────────────────────────────────────────────────────────
    if not SCHEMA_PATH.exists():
        print(f"FATAL: Schema not found at {SCHEMA_PATH}")
        return 1
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    print(f"Schema loaded: {SCHEMA_PATH}")

    # ── Load datasets ──────────────────────────────────────────────────────
    if BACKEND_DATASETS.exists():
        datasets_path = BACKEND_DATASETS
    elif REFERENCE_DATASETS.exists():
        datasets_path = REFERENCE_DATASETS
    else:
        print(f"FATAL: No dataset file found at\n  {BACKEND_DATASETS}\n  {REFERENCE_DATASETS}")
        return 1

    datasets = load_json(datasets_path)
    print(f"Datasets loaded: {datasets_path}  ({len(datasets)} entries)\n")

    if not isinstance(datasets, list):
        print("FATAL: Dataset file must contain a JSON array.")
        return 1

    # ── Validate each entry ────────────────────────────────────────────────
    passed = 0
    failed = 0

    for idx, entry in enumerate(datasets):
        dataset_id = entry.get("dataset_id", f"<index-{idx}>")
        errors = list(validator.iter_errors(entry))
        if errors:
            failed += 1
            print(f"  FAIL  [{idx+1:>2}] {dataset_id}")
            for err in errors:
                path = ".".join(str(p) for p in err.absolute_path) or "(root)"
                print(f"        └─ {path}: {err.message}")
        else:
            passed += 1
            print(f"  PASS  [{idx+1:>2}] {dataset_id}")

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Total: {len(datasets)}  |  Passed: {passed}  |  Failed: {failed}")
    print(f"{'='*60}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
