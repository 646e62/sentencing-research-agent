"""
Main CLI entrypoint for orchestrating project modules.
"""

from __future__ import annotations

import json
import os
from typing import Optional, Any

import typer
import pandas as pd

from case_data_processing import (
    process_text,
    html_to_markdown,
    split_header_and_body,
    clean_text_section,
    extract_citation,
    remove_after_string,
    split_body_into_paragraphs,
)
from metadata_processing import get_case_relations, get_metadata_from_citation
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


def _load_markdown_from_html(filename: str) -> str:
    file_name = filename.strip()
    if not file_name.lower().endswith(".html"):
        file_name = f"{file_name}.html"

    input_path = os.path.join("data", "html", file_name)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    with open(input_path, "r", encoding="utf-8") as handle:
        html = handle.read()

    return html_to_markdown(html)


def _get_clean_header(filename: str) -> str:
    markdown = _load_markdown_from_html(filename)
    header, _body = split_header_and_body(markdown)
    return clean_text_section(header)


def _get_body(filename: str) -> str:
    markdown = _load_markdown_from_html(filename)
    _header, body = split_header_and_body(markdown)
    return body


@app.command("metadata")
def metadata_cmd(
    citation: str = typer.Argument(..., help="Citation string (e.g., '2024 SKCA 79')"),
    local: bool = typer.Option(False, "--local", help="Skip CanLII API calls"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Get metadata from a citation."""
    metadata = get_metadata_from_citation(citation, include_relations=not local)
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
    result = get_case_relations(citation)
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


@app.command("html-to-md")
def html_to_md_cmd(
    filename: str = typer.Argument(..., help="HTML filename (e.g., 'case.html' or 'case')"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Convert an HTML file in ./data/html to Markdown and print the result."""
    try:
        markdown = _load_markdown_from_html(filename)
    except FileNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)
    if json_output:
        typer.echo(json.dumps({"markdown": markdown}, indent=2))
        return

    typer.echo(markdown)


@app.command("header")
def split_header_cmd(
    filename: str = typer.Argument(..., help="HTML filename (e.g., 'case.html' or 'case')"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Extract the header from an HTML file in ./data/html and print it."""
    try:
        header = _get_clean_header(filename)
    except FileNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

    if json_output:
        typer.echo(json.dumps({"header": header}, indent=2))
        return

    typer.echo(header)


@app.command("citation")
def citation_cmd(
    filename: str = typer.Argument(..., help="HTML filename (e.g., 'case.html' or 'case')"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Extract the citation from an HTML file in ./data/html."""
    try:
        header = _get_clean_header(filename)
    except FileNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

    citation = extract_citation(header)
    if json_output:
        typer.echo(json.dumps({"citation": citation}, indent=2))
        return

    if not citation:
        typer.echo("No citation found.")
        raise typer.Exit(code=1)

    typer.echo(citation)


@app.command("body")
def body_cmd(
    filename: str = typer.Argument(..., help="HTML filename (e.g., 'case.html' or 'case')"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Extract the body from an HTML file in ./data/html."""
    try:
        body = _get_body(filename)
    except FileNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

    body = remove_after_string(body, "Back to top")
    paragraphs = split_body_into_paragraphs(body)

    if json_output:
        typer.echo(json.dumps({"body": paragraphs}, indent=2))
        return

    for idx, paragraph in enumerate(paragraphs, start=1):
        typer.echo(f"--- Paragraph {idx} ---")
        typer.echo(paragraph)


if __name__ == "__main__":
    app()
