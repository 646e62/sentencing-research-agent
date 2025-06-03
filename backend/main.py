from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bs4 import BeautifulSoup
from backend.text_processing import html_to_markdown, extract_citation, get_metadata_from_citation, clean_header, split_header_and_body

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
    """Convert HTML to Markdown, split into cleaned header and body."""
    markdown = html_to_markdown(payload.html)
    cleaned_markdown = clean_header(markdown)
    header, body = split_header_and_body(cleaned_markdown)
    # Split body into paragraphs
    body_paragraphs = [p.strip() for p in body.split("\n__\n") if p.strip()]
    statistics = {"paragraph_count": len(body_paragraphs)}
    return {
        "cleaned_header": header,
        "body_paragraphs": body_paragraphs,
        "statistics": statistics
    }

