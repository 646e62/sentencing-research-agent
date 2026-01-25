"""

This module provides tools for processing data using the Google Gemini API.
"""

import os
import logging
from google import genai
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DocumentStructure(BaseModel):
    headings: str
    heading_number: str
    paragraph_index: int

client = genai.Client()

# Have the client review the body paragraphs and identify the headings and
# subheadings.
def body_headings(body_paragraphs: list[str]) -> list[DocumentStructure]:
    """
    Identify the headings and subheadings in the body paragraphs.
    """

    prompt = f"""
    Review the following paragraphs and the headings they contain. Return the
    heading, the heading number or letter, and the paragraph index the heading
    refers to. If there is a heading letter or number, please ensure it is not 
    duplicated in the "heading" value:

    {body_paragraphs}
    """

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": list[DocumentStructure],
        },
    )

    return response.parsed
