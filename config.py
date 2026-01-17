"""
Configuration helpers for local secrets.
"""

import os


class Config:
    """
    Centralized access to environment-backed configuration.
    """

    CANLII_API_KEY = os.getenv("CANLII_API_KEY", "")
