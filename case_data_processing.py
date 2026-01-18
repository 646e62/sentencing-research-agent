"""
Case data processing tools.

This module provides tools for processing case data from CanLII case files into
structured data that can then be used to generate sentencing data and case 
summaries.
"""

import re
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List, TypedDict

import html2text
import pandas as pd

from metadata_processing import (
    get_metadata_from_citation,
)

logger = logging.getLogger(__name__)

class ProcessedTextResult(TypedDict):
    _body: str
    header: Optional[str]
    processing_log: List[str]

def html_to_markdown(html_content: str) -> str:
    """Convert HTML to Markdown format."""
    h = html2text.HTML2Text()
    h.ignore_links = True
    markdown = h.handle(html_content)
    return markdown

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

def split_header_and_body(
    text: str,
    target_string: str = "\n\n__\n",
) -> Tuple[str, str]:
    """
    Split text into header and body.

    The text is split into chunks using `target_string` as a marker.
    - The 4th non-empty chunk (index 3) is used as the header (after cleaning).
    - Everything after the 4th chunk is joined with blank lines as the body.
    - If fewer than 4 non-empty chunks exist, header is "" and body is the full text.
    """

    if not target_string:
        # No marker: nothing to split reliably
        return "", text.strip()

    # Split manually to preserve behaviour closest to original function
    raw_chunks = []
    start_idx = 0

    while True:
        marker_idx = text.find(target_string, start_idx)
        if marker_idx == -1:
            raw_chunks.append(text[start_idx:])
            break
        raw_chunks.append(text[start_idx:marker_idx])
        start_idx = marker_idx + len(target_string)

    # Remove empty/whitespace-only chunks
    chunks = [chunk.strip() for chunk in raw_chunks if chunk.strip()]

    # Not enough chunks to have a header; return whole text as body
    if len(chunks) < 4:
        return "", text.strip()

    raw_header = chunks[3].strip()
    header = clean_header(raw_header)

    # Body is everything after the 4th chunk, joined with blank lines
    body_chunks = chunks[4:]
    body = "\n\n".join(body_chunks).strip() if body_chunks else ""

    return header, body

def extract_citation(header: str) -> str:
    """Extract citation from header text."""
    try:
        # Look for the start marker
        start_marker = "## "
        start_pos = header.find(start_marker)
        if start_pos == -1:
            logger.warning("No citation start marker '## ' found in header")
            return ""
            
        # Start position after the marker
        start_pos += len(start_marker)
        
        # Look for the end marker
        end_marker = " * "
        end_pos = header.find(end_marker, start_pos)
        if end_pos == -1:
            logger.warning("No citation end marker '(CanLII)' found in header")
            return ""
            
        # Extract the citation
        citation = header[start_pos:end_pos].strip()
        return citation
        
    except Exception as e:
        logger.error(f"Error extracting citation: {str(e)}")
        return ""

def extract_canlii_summary(header: str) -> Optional[str]:
    """Extract CanLII summary section from header if it exists."""
    try:
        # Look for the start marker
        start_marker = "### Facts"
        start_pos = header.find(start_marker)
        if start_pos == -1:
            return None
            
        # Find the end marker
        end_marker = "_Generated on"
        end_pos = header.find(end_marker, start_pos)
        if end_pos == -1:
            return None
            
        # Extract and clean the summary section, including "### Facts"
        summary = header[start_pos:end_pos].strip()
        return summary if summary else None
        
    except Exception as e:
        logger.error(f"Error extracting CanLII summary: {str(e)}")
        return None

# Various text cleaning functions
def remove_after_string(text: str, target_string: str) -> str:
    """Removes footer text from the Markdown file."""
    index = text.find(target_string)
    if index != -1:
        return text[:index]
    return text

def replace_newlines(text: str) -> str:
    """Remove whitespace while preserving markdown formatting."""
    pattern = r"(?<!__)\n(?!__)"
    return re.sub(pattern, " ", text)

def remove_newline_prefix_space(text: str) -> str:
    """Remove space after newlines."""
    pattern = r"\n\s+"
    return re.sub(pattern, "\n", text)

def clean_text_section(text: str) -> str:
    """Clean and format a section of text."""
    text = replace_newlines(text)
    text = remove_newline_prefix_space(text)
    text = re.sub(r"  +", " ", text)  # Remove multiple spaces
    text = re.sub(r"\n\s*\n", "\n", text)  # Remove multiple newlines
    return text.strip()

def process_text(text: str, include_header: bool = False) -> ProcessedTextResult:
    """Process HTML content and return structured data."""
    try:
        logger.info("Starting document processing...")
        
        # Convert HTML to Markdown
        logger.info("Converting HTML to markdown format...")
        markdown_text = html_to_markdown(text)
        
        # Split into header and body
        logger.info("Splitting document into header and body sections...")
        header, body = split_header_and_body(markdown_text)
        
        # Remove footer from body
        body = remove_after_string(body, "Back to top")
        
        # Clean both sections
        logger.info("Cleaning and formatting text sections...")
        header = clean_text_section(header)
        body = clean_text_section(body)
        
        # Extract citation first
        logger.info("Extracting citation...")
        citation = extract_citation(header)
        if not citation:
            raise ValueError("Could not extract citation from header")
        logger.info(f"Found citation: {citation}")
        
        # Get all metadata from the citation
        logger.info("Extracting metadata from citation...")
        metadata = get_metadata_from_citation(citation)
        if not metadata:
            raise ValueError("Could not extract metadata from citation")
        
        # Extract CanLII summary but don't include in final output
        logger.info("Extracting CanLII summary...")
        canlii_summary = extract_canlii_summary(header)

        result: ProcessedTextResult = {
            "_body": body,  # Internal field
            "header": header if include_header else None,
            "metadata": metadata,
            "sentencing_data": sentencing_data,
            "processing_log": [
                "Citation extracted successfully",
                "Metadata extracted successfully",
                "Citations extracted successfully",
                "CanLII summary extracted"
            ]
        }
        
        # Add CanLII-specific log entries
        if api_response.get('error'):
            result['processing_log'].append(f"Error fetching citing cases: {api_response['error']}")
        else:
            result['processing_log'].append(f"Found {len(decisions_citing)} citing cases")
        
        result['processing_log'].extend([
            "Sentencing data analyzed successfully",
            "Case summary generated successfully"
        ])
        
        logger.info("Document processing completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error in process_text: {str(e)}")
        raise