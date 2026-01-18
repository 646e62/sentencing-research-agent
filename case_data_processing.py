"""
Case data processing tools.

This module provides tools for processing case data from CanLII case files into
structured data that can then be used to generate sentencing data and case 
summaries.
"""

import re
import logging
from typing import Any, Optional, TypedDict

import html2text

logger = logging.getLogger(__name__)

# Constants
# Citation markers
_CITATION_START_MARKER = "# "
_CITATION_END_MARKER = " (CanLII) "
_ENG_MARKER = "Loading paragraph markers __\n"
_FR_MARKER = "Chargement des marqueurs de paragraphe __\n"

# TypedDict for processed text result
class ProcessedTextResult(TypedDict):
    header: Optional[str]
    body: str
    metadata: dict[str, Any]
    processing_log: list[str]

def html_to_markdown(html_content: str) -> str:
    """Convert HTML to Markdown format."""
    
    h = html2text.HTML2Text()
    
    return h.handle(html_content)

# Header functions
def split_header_and_body(
    text: str,
    target_string: str = "\n\n__\n",
) -> tuple[str, str]:
    """
    Split raw Markdown into header and body using a marker string.

    The text is split into chunks using `target_string` as a marker.
    - The 4th non-empty chunk (index 3) is used as the header (after cleaning).
    - Everything after the 4th chunk is joined with `target_string` as the body.
    - If fewer than 4 non-empty chunks exist, the header is "" and the body
      is the full original text (stripped).
    """

    if not target_string:
        return "", text.strip()

    raw_chunks = text.split(target_string)
    chunks = [chunk.strip() for chunk in raw_chunks if chunk.strip()]

    if len(chunks) < 4:
        return "", text.strip()

    header = clean_header(chunks[3])

    body_chunks = chunks[4:]
    body = target_string.join(body_chunks).strip() if body_chunks else ""

    return header, body

def clean_header(header: str) -> str:
    """
    Remove known “loading paragraph markers” from a header and strip whitespace.

    If any known marker lines are present (English or French), everything up to
    and including the last such marker is removed. Otherwise the header is
    returned stripped as-is.
    """

    markers = [
        _ENG_MARKER,
        _FR_MARKER,
    ]

    last_end_pos = -1
    for marker in markers:
        pos = header.rfind(marker)
        if pos != -1:
            end_pos = pos + len(marker)
            if end_pos > last_end_pos:
                last_end_pos = end_pos

    if last_end_pos == -1:
        return header.strip()

    return header[last_end_pos:].strip()

def extract_citation(header: str) -> str:
    """
    Extract the case citation from the header text.

    Expects a header starting with '# ' and containing ' (CanLII) '.
    Returns the substring between these markers, or "" if not found.
    """

    start_pos = header.find(_CITATION_START_MARKER)
    if start_pos == -1:
        logger.warning("No citation start marker '%s' found in header", _CITATION_START_MARKER)
        return ""

    start_pos += len(_CITATION_START_MARKER)

    end_pos = header.find(_CITATION_END_MARKER, start_pos)
    if end_pos == -1:
        logger.warning("No citation end marker '%s' found in header", _CITATION_END_MARKER)
        return ""

    citation = header[start_pos:end_pos].strip()
    return citation

# Body functions
def split_body_into_paragraphs(body: str) -> list[str]:
    """
    Split the body into logical paragraphs.

    Paragraphs are separated by lines containing '__' (e.g. '\n__\n').
    Leading paragraph numbers in the form '[n] ' (e.g. '[12] ') are removed
    from each paragraph, if present.
    """

    if not body:
        return []

    parts = re.split(r"\n+__\n+", body)
    paragraphs: list[str] = []

    for part in parts:
        cleaned = part.strip()
        if not cleaned:
            continue

        # Remove hard-coded paragraph numbers
        prefix = cleaned[:10]
        marker_idx = prefix.find("] ")
        if marker_idx != -1:
            cleaned = cleaned[marker_idx + 2 :].lstrip()

        if cleaned:
            paragraphs.append(cleaned)

    return paragraphs

# Various text cleaning functions
def clean_text_section(text: str) -> str:
    """
    Clean and normalize a section of text from a case document.

    - Removes specific superfluous header text between '!' and the next 'PDF'.
    - Normalizes whitespace while preserving paragraph markers '__'.
    - Collapses multiple spaces/newlines and removes decorative separator runs.
    """

    # Removes specific superfluous header text
    bang_idx = text.find("!")
    if bang_idx != -1:
        pdf_idx = text.find("PDF", bang_idx)
        if pdf_idx != -1:
            text = text[:bang_idx] + text[pdf_idx + len("PDF"):]

    # Remove extraneous whitespace
    text = re.sub(r"(?<!__)\n(?!__)", " ", text)    # Remove whitespace between
                                                    # paragraphs
    text = re.sub(r"\n\s+", "\n", text)             # Remove space after 
                                                    # newlines
    text = re.sub(r"  +", " ", text)                # Remove multiple spaces
    text = re.sub(r"\n\s*\n", "\n", text)           # Remove multiple newlines
    text = re.sub(r"(?:\*\s+){2,}\*", "", text)     # Remove separator runs
    
    return text.strip()

def remove_after_string(text: str, target_string: str) -> str:
    """
    Truncate text at the first occurrence of `target_string`.

    Returns the substring from the start of `text` up to (but not including)
    the first occurrence of `target_string`. If the target string is not
    present, returns the original text unchanged.
    """

    index = text.find(target_string)
    if index != -1:
        return text[:index]
    return text
