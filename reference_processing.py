"""
Tools for fetching case relations from the CanLII case citator API.

This module provides tools for fetching case relations from the CanLII case citator API.
It includes functions for parsing citations, making API requests, and handling responses.
"""

import logging
import re
from typing import Dict, Any, Literal
import requests
from config import Config
from metadata_processing import _parse_citation

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 10

CaseReferenceType = Literal["citedCases", "citingCases", "citedLegislations"]

def get_case_relations(
    citation: str,
    caseref_type: CaseReferenceType = "citingCases",
    timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """
    Fetch related cases/legislation from the CanLII case citator API and
    add them into the metadata dict under the given caseref_type key.

    caseref_type: "citedCases", "citingCases", or "citedLegislations"
    """
    
    try:
        api_key = Config.CANLII_API_KEY
        if not api_key:
            raise ValueError("CANLII_API_KEY not found in environment variables")
        
        citation_data = _parse_citation(citation)
        if not citation_data or 'court' not in citation_data or 'uid' not in citation_data:
            raise ValueError(f"Could not parse citation: {citation}")
            
        # Convert court name to lowercase and clean up decision code
        court_name = citation_data['court'].lower()
        decision_code = citation_data['uid'].lower().replace('-', '')

        # CaseReferenceType is encoded in the URL path per CanLII docs
        url = (
            f"https://api.canlii.org/v1/caseCitator/en/"
            f"{court_name}/{decision_code}/{caseref_type}"
            f"?api_key={api_key}"
        )
        logger.info("Making CanLII API request")  # Don't log the URL with API key

        response = requests.get(url, timeout=timeout_seconds)

        if response.status_code == 429:
            logger.warning("CanLII API rate limit reached")
            return {
                "error": "Rate limit reached",
                caseref_type: [],
                "metadata": citation_data.get("metadata", {}),
            }
            
        if response.status_code != 200:
            logger.error(f"CanLII API error: {response.status_code}")
            return {
                "error": f"API error: {response.status_code}",
                caseref_type: [],
                "metadata": citation_data.get("metadata", {}),
            }

        data = response.json()
        items = data.get(caseref_type, [])

        return {
            caseref_type: items,
            "error": None,
            "metadata": citation_data.get("metadata", {}) or {},
        }

    except Exception as e:
        logger.error("Error fetching case relations: %s", e)
        return {"error": str(e), "citingCases": [], "citedCases": [], "metadata": None}

def get_cited_legislation(
    paragraphs: list[str],
) -> list[tuple[str, str | None, list[int]]]:
    """
    Find and compile a list of cited legislation from the given paragraphs.

    Returns a list of tuples containing the legislation name, citation, and
    a list of paragraph numbers where it appears.
    """

    _LEGISLATION = {
        "/en/ca/laws/stat/rsc-1985-c-c-46/latest/rsc-1985-c-c-46.html": "Criminal Code",
        "/en/ca/laws/stat/sc-1996-c-19/latest/sc-1996-c-19.html": "Controlled Drugs and Substances Act",
        "/en/ca/laws/stat/schedule-b-to-the-canada-act-1982-uk-1982-c-11/latest/schedule-b-to-the-canada-act-1982-uk-1982-c-11.html": "Charter",
        "/en/ca/laws/stat/rsc-1985-c-c-47/latest/rsc-1985-c-c-47.html": "Criminal Records Act",
        "/en/ca/laws/stat/sc-2001-c-27/latest/sc-2001-c-27.html": "Immigration and Refugee Protection Act",
    }
    
    # Create a regex that finds markdown links of the form [text](url)
    markdown_link_regex = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    # Map of legislation name to a list of paragraph numbers where it appears
    legislation_map: dict[tuple[str, str | None], list[int]] = {}
    
    for index, paragraph in enumerate(paragraphs, start=1):
        for match in markdown_link_regex.finditer(paragraph):
            paragraph_number = index
            url = match.group(2)
            section = None
    
            # Remove whitespace from the url
            url = url.replace(" ", "")

            # Skip over a url if it doesn't have the string "laws" in it
            if "laws" not in url:
                continue

            # Check for a # character in the url
            if "#" in url:
                url, section = url.split("#", 1)
                if "_smooth" in section:
                    section = section.replace("_smooth", "")

            if url in _LEGISLATION:
                url = _LEGISLATION[url]

            key = (url, section)
            if key not in legislation_map:
                legislation_map[key] = []
            legislation_map[key].append(paragraph_number)

    # Remove redundant paragraph numbers from null-section entries
    with_section: dict[str, set[int]] = {}
    for (name, section), paragraphs in legislation_map.items():
        if section:
            with_section.setdefault(name, set()).update(paragraphs)

    for (name, section), paragraphs in list(legislation_map.items()):
        if section is None and name in with_section:
            filtered = [p for p in paragraphs if p not in with_section[name]]
            legislation_map[(name, section)] = filtered

    return [
        (name, section, sorted(set(paragraphs)))
        for (name, section), paragraphs in legislation_map.items()
        if paragraphs
    ]
    