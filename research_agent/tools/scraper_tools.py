import io
import re
import urllib.parse
from typing import Optional
import requests
from bs4 import BeautifulSoup
from research_agent.config import config

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import trafilatura
except ImportError:
    trafilatura = None


def extract_pdf_content(content_bytes: bytes, max_chars: int) -> dict:
    """Extracts text from PDF bytes using pypdf."""
    if not PdfReader:
        return {
            "title": "PDF Document",
            "text": "[pypdf not available to parse PDF]",
            "success": False,
        }

    try:
        reader = PdfReader(io.BytesIO(content_bytes))
        num_pages = len(reader.pages)
        extracted = []
        # Read up to the first 10 pages to avoid excessive token length
        for page_idx in range(min(num_pages, 10)):
            page_text = reader.pages[page_idx].extract_text() or ""
            if page_text.strip():
                extracted.append(page_text.strip())

        full_text = "\n\n".join(extracted)
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + f"\n\n[...Truncated to {max_chars} characters...]"

        return {
            "title": f"PDF Document ({num_pages} pages)",
            "text": full_text.strip(),
            "success": bool(full_text.strip()),
        }
    except Exception as e:
        return {
            "title": "PDF Document",
            "text": f"[Error reading PDF: {e}]",
            "success": False,
        }


def scrape_url(url: str, max_chars: Optional[int] = None) -> dict:
    """
    Scrapes content from a web page or PDF and returns clean text and metadata.
    """
    if max_chars is None:
        max_chars = config.scrape_char_limit

    headers = {
        "User-Agent": config.user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        response = requests.get(url, headers=headers, timeout=config.timeout_seconds, allow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        
        # 1. Handle PDF documents (e.g. arXiv papers or whitepapers)
        if "application/pdf" in content_type or url.lower().split("?")[0].endswith(".pdf"):
            pdf_data = extract_pdf_content(response.content, max_chars)
            return {
                "url": url,
                "title": pdf_data["title"],
                "text": pdf_data["text"],
                "success": pdf_data["success"],
            }

        # 2. Check for HTML
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            return {
                "url": url,
                "title": "",
                "text": f"[Non-HTML/PDF content skipped: {content_type}]",
                "success": False,
            }

        html = response.text
        title = ""
        extracted_text = ""

        # Attempt 1: trafilatura (clean main article text)
        if trafilatura:
            try:
                extracted_text = trafilatura.extract(
                    html,
                    include_links=False,
                    include_images=False,
                    output_format="txt",
                ) or ""
            except Exception:
                extracted_text = ""

        # Attempt 2: BeautifulSoup extraction
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Clean noise tags and Wikipedia/boilerplate chrome
        noise_selectors = [
            "script", "style", "nav", "footer", "header", "noscript", "svg", "aside",
            ".mw-jump-link", ".vector-menu", "#mw-navigation", ".sidebar", ".navbox",
            ".infobox", ".toc", ".mw-editsection", "#toc", ".reference"
        ]
        for sel in noise_selectors:
            for el in soup.select(sel):
                el.decompose()

        # Extract meaningful paragraphs from article or main or body
        content_root = soup.find("main") or soup.find("article") or soup.find(id="mw-content-text") or soup.body
        if content_root:
            paragraphs = [p.get_text(" ", strip=True) for p in content_root.find_all("p") if len(p.get_text(strip=True)) > 40]
            if paragraphs:
                extracted_text = "\n\n".join(paragraphs)

        if not extracted_text or len(extracted_text.strip()) < 100:
            body_text = soup.get_text(separator="\n", strip=True)
            extracted_text = re.sub(r"\n{3,}", "\n\n", body_text)

        # Truncate to limit
        if len(extracted_text) > max_chars:
            extracted_text = extracted_text[:max_chars] + f"\n\n[...Truncated to {max_chars} characters...]"

        return {
            "url": url,
            "title": title or url,
            "text": extracted_text.strip(),
            "success": bool(extracted_text.strip()),
        }

    except Exception as e:
        return {
            "url": url,
            "title": "",
            "text": f"[Error fetching URL: {str(e)}]",
            "success": False,
        }

