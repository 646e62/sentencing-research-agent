"""

This module provides tools for processing data using the Google Gemini API.
"""

import os
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

client = genai.Client()

# Configure for structured output
model = "gemini-2.5-flash"
config = types.GenerateContentConfig(
    model=model,
    response_mime_type="application/json",
)

# Have the client review the body paragraphs and identify the headings and 
# subheadings.
def body_headings(body_paragraphs: list[str]) -> list[str]:
    """
    Identify the headings and subheadings in the body paragraphs.
    """
    prompt = f"""
    You are a helpful assistant that identifies the headings and subheadings in the body paragraphs.
    """
    response = client.generate_content(prompt)
    return response.text