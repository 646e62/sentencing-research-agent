"""
Tools for fetching case relations from the CanLII case citator API.

This module provides tools for fetching case relations from the CanLII case citator API.
It includes functions for parsing citations, making API requests, and handling responses.
"""

import logging
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
