"""
Metadata processing tools.

This module provides tools for generating and retrieving metadata using local 
rules and the CanLII API.
"""

import logging
from typing import Dict, Any, Optional, List, TypedDict, Union, Literal

import requests

from config import Config
import legal_citation_parser

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 10

class CitationMetadata(TypedDict):
    citation: str
    case_id: Optional[str]
    style_of_cause: Optional[str]
    atomic_citation: Optional[str]
    citation_type: Optional[str]
    official_reporter_citation: Optional[str]
    year: Optional[str]
    court: Optional[str]
    decision_number: Optional[str]
    jurisdiction: Optional[str]
    court_name: Optional[str]
    court_level: Optional[str]
    long_url: Optional[str]
    short_url: Optional[str]
    language: Optional[str]
    docket_number: Optional[str]
    decision_date: Optional[str]
    keywords: List[str]
    categories: List[str]
    cited_cases: List[Dict[str, Any]]
    citing_cases: List[Dict[str, Any]]

class CitingCasesSuccess(TypedDict):
    cases: List[Dict[str, Any]]
    error: None
    metadata: Optional[Dict[str, Any]]

class CitingCasesError(TypedDict):
    cases: List[Dict[str, Any]]
    error: str
    metadata: None

#CitingCasesResult = Union[CitingCasesSuccess, CitingCasesError]
CaseReferenceType = Literal["citedCases", "citingCases", "citedLegislations"]

def _parse_citation(citation: str) -> Optional[Dict[str, Any]]:
    """
    Parse a citation using the legal citation parser.

    Returns the parsed citation dict or None if parsing fails.
    """
    try:
        citation_data = legal_citation_parser.parse_citation(citation, metadata=True)
    except Exception as exc:
        logger.error("Error parsing citation %r: %s", citation, exc)
        return None

    if not citation_data:
        logger.warning("Could not parse citation: %s", citation)
        return None

    return citation_data

def get_metadata_from_citation(
    citation: str,
    include_relations: bool = True,
) -> Optional[CitationMetadata]:
    """Extract all metadata from a citation using the legal citation parser."""
    try:
        citation_data = _parse_citation(citation)
        if not citation_data:
            return None
        
        style_of_cause = citation_data.get('style_of_cause', '')
        atomic_citation = citation_data.get('atomic_citation', '')

        # Build the normalized citation string
        if style_of_cause and atomic_citation:
            formatted_citation = f"{style_of_cause}, {atomic_citation} (CanLII)"
        elif style_of_cause:
            formatted_citation = f"{style_of_cause} (CanLII)"
        elif atomic_citation:
            formatted_citation = f"{atomic_citation} (CanLII)"
        else:
            formatted_citation = citation

        # Map the fields from citation_data to our desired structure
        metadata: CitationMetadata = {
            "citation": formatted_citation,
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
            "categories": citation_data.get('categories', []),
        }

        if include_relations:
            cited_cases_result = get_case_relations(citation, "citedCases")
            citing_cases_result = get_case_relations(citation, "citingCases")
            metadata["cited_cases"] = cited_cases_result.get("citedCases", [])
            metadata["citing_cases"] = citing_cases_result.get("citingCases", [])
        
        return metadata
        
    except Exception as e:
        logger.error("Error getting metadata from citation: %s", e)
        return None

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
