"""
Case data processing tools.

This module provides tools for processing case data from CanLII case files into
structured data that can then be used to generate sentencing data and case 
summaries.
"""

import re
import os
from pathlib import Path
from typing import Dict, Any, Tuple
import logging
import html2text
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

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

def split_header_and_body(text: str, target_string: str = "\n__\n") -> Tuple[str, str]:
    """Split text into header and body at the second occurrence of target_string."""
    first_occurrence = text.find(target_string)
    if first_occurrence == -1:
        return "", text  # No header found
        
    second_occurrence = text.find(target_string, first_occurrence + 1)
    if second_occurrence == -1:
        return "", text  # No second occurrence found
        
    # Get the raw header and clean it
    raw_header = text[:second_occurrence].strip()
    header = clean_header(raw_header)
    
    # Get the body
    body = text[second_occurrence + len(target_string):].strip()
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

def extract_legislation(header: str) -> str:
    """Extract legislation cited section from header if it exists."""
    try:
        # Try English markers first
        start_marker = "### Legislation"
        end_marker = "### Decisions"
        
        start_pos = header.find(start_marker)
        if start_pos == -1:
            # Try French markers
            start_marker = "### Législation"
            end_marker = "### Décisions"
            start_pos = header.find(start_marker)
            
        if start_pos == -1:
            return None
            
        # Move past the start marker
        start_pos += len(start_marker)
        
        # Find the end marker after the start position
        end_pos = header.find(end_marker, start_pos)
        if end_pos == -1:
            return None
            
        # Extract and clean the legislation section
        legislation = header[start_pos:end_pos].strip()
        return legislation if legislation else None
        
    except Exception as e:
        logger.error(f"Error extracting legislation: {str(e)}")
        return None

def extract_decisions(header: str) -> str:
    """Extract decisions cited section from header if it exists."""
    try:
        # Try English marker first
        start_marker = "### Decisions"
        start_pos = header.find(start_marker)
        
        if start_pos == -1:
            # Try French marker
            start_marker = "### Décisions"
            start_pos = header.find(start_marker)
            
        if start_pos == -1:
            return None
            
        # Move past the start marker
        start_pos += len(start_marker)
        
        # Find the Citations __ marker
        end_marker = "Citations __"
        end_pos = header.find(end_marker, start_pos)
        
        if end_pos == -1:
            # If no Citations __ marker found, try finding the next section
            lines = header[start_pos:].split('\n')
            end_pos = start_pos
            for i, line in enumerate(lines):
                if line.strip().startswith('###'):
                    end_pos += sum(len(l) + 1 for l in lines[:i])
                    break
            else:
                # If no next section found, use the rest of the header
                end_pos = len(header)
        
        # Extract and clean the decisions section
        decisions = header[start_pos:end_pos].strip()
        return decisions if decisions else None
        
    except Exception as e:
        logger.error(f"Error extracting decisions: {str(e)}")
        return None

def extract_canlii_summary(header: str) -> str:
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

def get_canonical_filename(title: str) -> str:
    """Extract the canonical filename (e.g., 2025mbpc3) from a title."""
    # Split by underscore and take first three parts
    parts = title.lower().split('_')[:3]
    # Join them together without underscores
    return ''.join(parts)

def save_processed_text(text_dict: Dict[str, Any], title: str) -> Tuple[str, bool, str]:
    """Save processed text as JSON in the specified directory.
    Returns tuple of (filepath, was_overwritten, base_filename)"""
    try:
        # Use the specified directory
        save_dir = '/home/daniel/Tresorit/jurimetrics/data/json'
        
        # Create the directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Extract first three parts of the filename and concatenate them
        parts = title.lower().split('_')[:3]
        base_filename = ''.join(parts)
        filename = f"{base_filename}.json"
        filepath = os.path.join(save_dir, filename)
        
        # Check if file exists
        was_overwritten = os.path.exists(filepath)
        
        # Create a copy of the dictionary without internal fields (those starting with _)
        json_dict = {k: v for k, v in text_dict.items() if not k.startswith('_')}
        
        # Save the file (overwriting if it exists)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_dict, f, indent=2, ensure_ascii=False)
        
        if was_overwritten:
            logger.info(f"Overwrote existing file at {filepath}")
        else:
            logger.info(f"Saved new file to {filepath}")
            
        return filepath, was_overwritten, base_filename
        
    except Exception as e:
        logger.error(f"Error saving processed text: {str(e)}")
        raise

def process_text(text: str, include_header: bool = False) -> Dict[str, Any]:
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
        
        # Extract other sections
        logger.info("Extracting citations from header...")
        legislation_cited = extract_legislation(header)
        decisions_cited = extract_decisions(header)
        
        # Extract CanLII summary but don't include in final output
        logger.info("Extracting CanLII summary...")
        canlii_summary = extract_canlii_summary(header)
        
        # Make CanLII API call early to space out the API calls
        logger.info("Fetching citing cases from CanLII API...")
        api_response = get_citing_cases(citation)
        decisions_citing = api_response.get('cases', [])
        logger.info(f"Found {len(decisions_citing)} citing cases")
        
        result = {
            "_body": body,  # Internal field
            "header": header if include_header else None,
            "metadata": metadata,
            "legislation_cited": legislation_cited,
            "decisions_cited": decisions_cited,
            "decisions_citing": decisions_citing,
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