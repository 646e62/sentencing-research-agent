"""
Configuration helpers for local secrets.
"""

import os

try:
    from dotenv import load_dotenv
except ImportError:  # optional dependency
    load_dotenv = None


if load_dotenv:
    load_dotenv()


class Config:
    """
    Centralized access to environment-backed configuration.
    """

    CANLII_API_KEY = os.getenv("CANLII_API_KEY", "")
