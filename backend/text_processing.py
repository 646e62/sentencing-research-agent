import re
from bs4 import BeautifulSoup
import requests
import os
from pathlib import Path
from typing import Dict, Any, Tuple
import logging
import html2text
import json
import legal_citation_parser

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
    """Split text into header and body at the first occurrence of target_string."""
    first_occurrence = text.find(target_string)
    if first_occurrence == -1:
        return "", text  # No header found
    # Get the raw header and clean it
    raw_header = text[:first_occurrence].strip()
    header = clean_header(raw_header)
    # Get the body
    body = text[first_occurrence + len(target_string):].strip()
    return header, body

def extract_citation(header: str) -> str:
    logger.debug(f"extract_citation: Received header (first 500 chars): {header[:500]!r}")
    print(f"[DEBUG] extract_citation: header (first 500 chars): {header[:500]!r}")
    print(f"[DEBUG] extract_citation: Searching for start marker '## '")
    """Extract citation from header text."""
    try:
        # Look for the start marker
        start_marker = "## "
        start_pos = header.find(start_marker)
        print(f"[DEBUG] extract_citation: start_pos for marker '## ': {start_pos}")
        if start_pos == -1:
            logger.warning("No citation start marker '## ' found in header")
            print("[DEBUG] extract_citation: No citation start marker found.")
            return None
        
        # Find the end marker
        end_marker = "\n"
        end_pos = header.find(end_marker, start_pos + len(start_marker))
        print(f"[DEBUG] extract_citation: end_pos for marker '\\n': {end_pos}")
        if end_pos == -1:
            end_pos = len(header)
        
        # Extract the citation
        citation = header[start_pos + len(start_marker):end_pos].strip()
        logger.debug(f"extract_citation: Extracted citation: {citation!r}")
        print(f"[DEBUG] extract_citation: Extracted citation: {citation!r}")
        return citation
        
    except Exception as e:
        logger.error(f"Error extracting citation: {str(e)}")
        print(f"[DEBUG] extract_citation: Exception: {e}")
        return ""

def get_metadata_from_citation(citation: str) -> Dict[str, Any]:
    logger.debug(f"get_metadata_from_citation: Received citation: {citation!r}")
    print(f"[DEBUG] legal_citation_parser input: {citation!r}")
    """Extract all metadata from a citation using the legal citation parser."""
    try:
        # Parse the citation with metadata flag
        citation_data = legal_citation_parser.parse_citation(citation, metadata=True)
        logger.debug(f"get_metadata_from_citation: Parsed citation data: {citation_data!r}")
        
        if not citation_data:
            logger.warning(f"Could not parse citation: {citation}")
            return {}
            
        # Map the fields from citation_data to our desired structure
        metadata = {
            "citation": citation,  # Keep the original citation string
            "case_id": citation_data.get('uid'),
            "style_of_cause": citation_data.get('style_of_cause'),
            "atomic_citation": citation_data.get('atomic_citation'),
            "citation_type": citation_data.get('citation_type'),
            "official_reporter_citation": citation_data.get('official_reporter_citation'),
            "year": citation_data.get('year'),
            "court": citation_data.get('court'),
            "decision_number": citation_data.get('decision_number'),
            "jurisdiction": citation_data.get('jurisdiction'),
            "court_name": citation_data.get('court_name'),
            "court_level": citation_data.get('court_level'),
            "long_url": citation_data.get('long_url'),
            "short_url": citation_data.get('short_url'),
            "language": citation_data.get('language'),
            "docket_number": citation_data.get('docket_number'),
            "decision_date": citation_data.get('decision_date'),
            "keywords": citation_data.get('keywords', []),
            "categories": citation_data.get('categories', [])
        }
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error getting metadata from citation: {str(e)}")
        return {}

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
        logger.debug(f"extract_canlii_summary: start_pos for marker '{start_marker}': {start_pos}")
        if start_pos == -1:
            logger.debug("extract_canlii_summary: Start marker not found.")
            return None
            
        # Find the end marker
        end_marker = "_Generated on"
        end_pos = header.find(end_marker, start_pos)
        logger.debug(f"extract_canlii_summary: end_pos for marker '{end_marker}': {end_pos}")
        if end_pos == -1:
            logger.debug("extract_canlii_summary: End marker not found.")
            return None
            
        # Extract and clean the summary section, including "### Facts"
        summary = header[start_pos:end_pos].strip()
        logger.debug(f"extract_canlii_summary: Extracted summary (first 500 chars): {summary[:500]!r}")
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

def get_citing_cases(citation: str) -> Dict:
    """Fetch cases that cite this decision from CanLII API."""
    try:
        api_key = Config.CANLII_API_KEY
        if not api_key:
            raise ValueError("CANLII_API_KEY not found in environment variables")
        
        # Parse the citation with metadata flag
        citation_data = legal_citation_parser.parse_citation(citation, metadata=True)
        
        if not citation_data or 'court' not in citation_data or 'uid' not in citation_data:
            raise ValueError(f"Could not parse citation: {citation}")
            
        # Convert court name to lowercase and clean up decision code
        court_name = citation_data['court'].lower()
        decision_code = citation_data['uid'].lower().replace('-', '')
        
        url = f"https://api.canlii.org/v1/caseCitator/en/{court_name}/{decision_code}/citingCases?api_key={api_key}"
        logger.info("Making CanLII API request")  # Don't log the URL with API key
        
        response = requests.get(url)
        
        if response.status_code == 429:
            logger.warning("CanLII API rate limit reached")
            return {"error": "Rate limit reached", "cases": [], "metadata": None}
            
        if response.status_code != 200:
            logger.error(f"CanLII API error: {response.status_code}")
            return {"error": f"API error: {response.status_code}", "cases": [], "metadata": None}
            
        data = response.json()
        citing_cases = data.get('citingCases', [])
        
        # Include the metadata from the citation parser
        return {
            "cases": citing_cases,
            "error": None,
            "metadata": citation_data.get('metadata', {})
        }
        
    except Exception as e:
        logger.error(f"Error fetching citing cases: {str(e)}")
        return {"error": str(e), "cases": [], "metadata": None}