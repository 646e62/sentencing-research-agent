"""
Main CLI entrypoint for orchestrating project modules.
"""

from __future__ import annotations

import json
from typing import Optional, Any

import typer
import pandas as pd

from case_data_processing import process_text
from metadata_processing import get_citing_cases, get_metadata_from_citation
from sentencing_data_processing import process_master_row, load_master_csv

app = typer.Typer(help="Sentencing research CLI")

def _make_json_safe(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, dict):
        return {k: _make_json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_make_json_safe(v) for v in value]
    return value


@app.command("metadata")
def metadata_cmd(
    citation: str = typer.Argument(..., help="Citation string (e.g., '2024 SKCA 79')"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Get metadata from a citation."""
    metadata = get_metadata_from_citation(citation)
    if json_output:
        typer.echo(json.dumps(_make_json_safe(metadata), indent=2))
        return

    if not metadata:
        typer.echo("No metadata found.")
        raise typer.Exit(code=1)

    typer.echo("Metadata")
    for key, value in metadata.items():
        typer.echo(f"- {key}: {value}")


@app.command("citing-cases")
def citing_cases_cmd(
    citation: str = typer.Argument(..., help="Citation string (e.g., '2024 SKCA 79')"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Get cases that cite a decision."""
    result = get_citing_cases(citation)
    if json_output:
        typer.echo(json.dumps(_make_json_safe(result), indent=2))
        return

    if result.get("error"):
        typer.echo(f"Error: {result['error']}")
        raise typer.Exit(code=1)

    cases = result.get("cases", [])
    typer.echo(f"Found {len(cases)} citing cases.")


@app.command("sentencing-row")
def sentencing_row_cmd(
    row_index: int = typer.Option(0, "--row-index", help="Row index in master.csv"),
    master_file: str = typer.Option("data/case/master.csv", "--master", help="Path to master.csv"),
    offences_file: str = typer.Option(
        "data/offence/all-criminal-offences-current.csv",
        "--offences",
        help="Path to offences CSV",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Parse a row from master.csv and display results."""
    df = load_master_csv(master_file)
    if df.empty:
        typer.echo("Master CSV is empty.")
        raise typer.Exit(code=1)

    row_index = max(0, min(row_index, len(df) - 1))
    row = df.iloc[row_index]
    parsed = process_master_row(row, offences_file=offences_file, verbose=False)

    if json_output:
        typer.echo(json.dumps(_make_json_safe(parsed), indent=2))
        return

    uid = parsed.get("uid", {})
    typer.echo("Sentencing Row")
    typer.echo(f"- UID: {uid.get('case_id')}_{uid.get('docket')}_{uid.get('count')}_{uid.get('defendant')}")
    typer.echo(f"- Offence: {parsed.get('offence', {}).get('offence_name')}")
    typer.echo(f"- Date: {parsed.get('date', {})}")
    typer.echo(f"- Jail (days): {parsed.get('jail', {}).get('total_days')}")
    typer.echo(f"- Conditions: {parsed.get('conditions', {})}")


@app.command("case-text")
def case_text_cmd(
    input_path: str = typer.Argument(..., help="Path to HTML case file"),
    include_header: bool = typer.Option(False, "--include-header", help="Include header in output"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Process a case HTML file and display results."""
    with open(input_path, "r", encoding="utf-8") as handle:
        html = handle.read()

    result = process_text(html, include_header=include_header)

    if json_output:
        typer.echo(json.dumps(_make_json_safe(result), indent=2))
        return

    typer.echo("Case Text Summary")
    metadata = result.get("metadata") or {}
    typer.echo(f"- Citation: {metadata.get('citation')}")
    typer.echo(f"- Court: {metadata.get('court_name')}")
    typer.echo(f"- Decision date: {metadata.get('decision_date')}")
    typer.echo(f"- Citing cases: {len(result.get('decisions_citing', []))}")


if __name__ == "__main__":
    app()
