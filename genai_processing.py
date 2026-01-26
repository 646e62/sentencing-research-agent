"""

This module provides tools for processing data using the Google Gemini API.
"""

import os
import logging
import textwrap
from google import genai
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DocumentStructure(BaseModel):
    heading: str
    heading_id: str
    paragraph_index: int

class CaseSummary(BaseModel):
    summary: str

client = genai.Client()

# Have the client review the body paragraphs and identify the headings and
# subheadings.
def body_headings(body_paragraphs: list[str],
    model: str = "gemini-2.5-flash-lite") -> list[DocumentStructure]:
    """
    Identify the headings and subheadings in the body paragraphs.
    """

    prompt = f"""
    Review the following paragraphs and the headings they contain. Return the
    heading, the heading number or letter (or None if there is no heading number 
    or letter), and the paragraph index the heading refers to.

    The heading number should be an alphanumeric string, like a Roman numeral 
    or a number in an enumerated list. It should not simply be a duplicate of
    the heading text.

    {body_paragraphs}
    """

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": list[DocumentStructure],
        },
    )

    return response.parsed

def generate_summary(body_paragraphs: list[str],
    model: str = "gemini-2.5-flash-lite") -> str:
    """
    Generate a summary of the body paragraphs.
    """

    prompt = f"""
    Summarize this case in five to ten lines:

    {body_paragraphs}
    """

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": CaseSummary,
        },
    )

    # Ensure the summary is wrapped to 80 characters
    summary = response.parsed.summary
    summary = textwrap.fill(summary, width=80)

    return summary
