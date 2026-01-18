"""
CLI tool for retrieving metadata from a citation.
"""

import argparse
import json

from metadata_processing import get_metadata_from_citation


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="Fetch metadata for a citation")
    parser.add_argument("citation", help="Citation string (e.g., '2024 SKCA 79')")
    args = parser.parse_args()

    metadata = get_metadata_from_citation(args.citation)
    if not metadata:
        print("No metadata found.")
        return 1

    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
