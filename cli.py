"""
CLI entrypoint for the sentencing research tools.
"""

import argparse
import json
import logging
import os
from typing import Any

import pandas as pd

from sentencing_data_processing import (
    JsonValue,
    load_master_csv,
    process_master_row,
    validate_master_schema,
)


def _make_json_safe(value: Any) -> JsonValue:
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, dict):
        return {k: _make_json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_make_json_safe(v) for v in value]
    return value


def run_cli() -> int:
    """
    Minimal CLI for validating and sampling master.csv parsing.
    """
    parser = argparse.ArgumentParser(description="Sentencing data processing helpers")
    parser.add_argument(
        "--master",
        default="data/case/master.csv",
        help="Path to master CSV",
    )
    parser.add_argument(
        "--offences",
        default="data/offence/all-criminal-offences-current.csv",
        help="Path to offences CSV",
    )
    parser.add_argument(
        "--row-index",
        type=int,
        default=0,
        help="Row index to parse from master CSV",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate schema, do not parse rows",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress printing during row parsing",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO)
    df = load_master_csv(args.master)
    schema = validate_master_schema(df)
    if schema["missing"]:
        print(f"Missing columns: {schema['missing']}")
        return 1
    if schema["extra"]:
        print(f"Extra columns: {schema['extra']}")

    if args.validate_only:
        print("Schema validation passed.")
        return 0

    if df.empty:
        print("Master CSV is empty.")
        return 1

    row_index = max(0, min(args.row_index, len(df) - 1))
    row = df.iloc[row_index]
    parsed = process_master_row(row, offences_file=args.offences, verbose=not args.quiet)

    uid = parsed.get("uid", {})
    filename_parts = [
        uid.get("case_id") or "unknown",
        uid.get("docket") or "unknown",
        uid.get("count") or "unknown",
        uid.get("defendant") or "unknown",
    ]
    output_dir = os.path.join(".", "data", "json", "sentencing-data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "_".join(filename_parts) + ".json")

    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(_make_json_safe(parsed), output_file, indent=2)

    if not args.quiet:
        print(f"Wrote parsed output to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
