"""
Case data processing tools.

This module provides tools for processing case data from CanLII case files into
structured data that can then be used to generate sentencing data and case 
summaries.
"""

import re
import logging
from typing import Dict, Any, Tuple, Optional, List, TypedDict

import html2text

logger = logging.getLogger(__name__)

# Constants
# Citation markers
CITATION_START_MARKER = "# "
CITATION_END_MARKER = " (CanLII) "

# TypedDict for processed text result
class ProcessedTextResult(TypedDict):
    header: Optional[str]
    body: str
    metadata: Dict[str, Any]
    processing_log: List[str]

def html_to_markdown(html_content: str) -> str:
    """Convert HTML to Markdown format."""
    h = html2text.HTML2Text()
    h.ignore_links = True
    markdown = h.handle(html_content)
    return markdown

# Header functions
def split_header_and_body(
    text: str,
    target_string: str = "\n\n__\n",
) -> Tuple[str, str]:
    """
    Split text into header and body.

    The text is split into chunks using `target_string` as a marker.
    - The 4th non-empty chunk (index 3) is used as the header (after cleaning).
    - Everything after the 4th chunk is joined with the target string as the body.
    - If fewer than 4 non-empty chunks exist, header is "" and body is the full text.
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
    """Remove loading markers and clean up header text."""
    # Define loading markers in both languages
    eng_marker = "Loading paragraph markers __\n"
    fr_marker = "Chargement des marqueurs de paragraphe __\n"
    
    # Find the last occurrence of either marker
    eng_pos = header.rfind(eng_marker)
    fr_pos = header.rfind(fr_marker)
    
    # Get the position after the last marker found
    if eng_pos != -1 and fr_pos != -1:
        # Both markers found, use the later one
        start_pos = max(eng_pos + len(eng_marker), fr_pos + len(fr_marker))
    elif eng_pos != -1:
        start_pos = eng_pos + len(eng_marker)
    elif fr_pos != -1:
        start_pos = fr_pos + len(fr_marker)
    else:
        # No markers found, return as is
        return header.strip()
    
    # Return everything after the marker
    return header[start_pos:].strip()

def extract_citation(header: str) -> str:
    """Extract citation from header text."""
    start_pos = header.find(CITATION_START_MARKER)
    if start_pos == -1:
        logger.warning("No citation start marker '%s' found in header", CITATION_START_MARKER)
        return ""

    start_pos += len(CITATION_START_MARKER)

    end_pos = header.find(CITATION_END_MARKER, start_pos)
    if end_pos == -1:
        logger.warning("No citation end marker '%s' found in header", CITATION_END_MARKER)
        return ""

    citation = header[start_pos:end_pos].strip()
    return citation

# Body functions
def split_body_into_paragraphs(body: str) -> List[str]:
    """Split body into paragraphs using the marker line."""

    if not body:
        return []

    parts = re.split(r"\n+__\n+", body)
    paragraphs: List[str] = []

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
    """Clean and format a section of text."""

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
    """Removes footer text from the Markdown file."""
    index = text.find(target_string)
    if index != -1:
        return text[:index]
    return text
