from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bs4 import BeautifulSoup
from backend.text_processing import html_to_markdown, extract_citation, get_metadata_from_citation

app = FastAPI()

# Allow CORS for local extension development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HTMLPayload(BaseModel):
    html: str

@app.post("/extract-markdown")
def extract_markdown(payload: HTMLPayload):
    """Convert HTML to Markdown using html_to_markdown utility."""
    markdown = html_to_markdown(payload.html)
    return {"markdown": markdown}

