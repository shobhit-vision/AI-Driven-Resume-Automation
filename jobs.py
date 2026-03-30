"""
jobs.py — ResumeAI Pro · Job Extraction Module
Robust multi-strategy job extraction from URLs, text, and files.
Handles LinkedIn, Indeed, Naukri, Glassdoor, and generic pages.
"""

import re
import json
import time
import base64
from io import BytesIO
from typing import Optional
from urllib.parse import urlparse, urljoin

# ── Optional imports ──────────────────────────────────────────────────────────
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

try:
    from bs4 import BeautifulSoup
    BS4_OK = True
except ImportError:
    BS4_OK = False

try:
    import trafilatura
    TRAFILATURA_OK = True
except ImportError:
    TRAFILATURA_OK = False

try:
    import PyPDF2
    import pdfplumber
    PDF_OK = True
except ImportError:
    PDF_OK = False

try:
    from docx import Document as DocxDocument
    DOCX_OK = True
except ImportError:
    DOCX_OK = False

from settings import (
    GROQ_KEY, MAIN_MODEL,
    SCRAPE_TIMEOUT, SCRAPE_MAX_LINES, SCRAPE_MIN_LINE_LEN,
)

# ─────────────────────────────────────────────────────────────────────────────
# CORS-safe request session
# ─────────────────────────────────────────────────────────────────────────────

# Rotating user agents to avoid bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

_UA_IDX = 0

def _get_ua() -> str:
    global _UA_IDX
    ua = USER_AGENTS[_UA_IDX % len(USER_AGENTS)]
    _UA_IDX += 1
    return ua


def _build_session() -> "requests.Session":
    """Build a robust, retry-enabled requests session."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _headers(referer: str = "") -> dict:
    """Generate browser-like headers to pass CORS / anti-bot checks."""
    return {
        "User-Agent":                _get_ua(),
        "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language":           "en-US,en;q=0.9",
        "Accept-Encoding":           "gzip, deflate, br",
        "Connection":                "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest":            "document",
        "Sec-Fetch-Mode":            "navigate",
        "Sec-Fetch-Site":            "none",
        "Cache-Control":             "max-age=0",
        **({"Referer": referer} if referer else {}),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Domain-specific extractors
# ─────────────────────────────────────────────────────────────────────────────

def _extract_linkedin(soup: "BeautifulSoup") -> str:
    """LinkedIn job page extractor."""
    parts = []
    for sel in [
        ".jobs-description__content",
        ".jobs-box__html-content",
        ".description__text",
        "[data-test-id='job-details']",
        ".job-view-layout",
        "article",
    ]:
        el = soup.select_one(sel)
        if el:
            parts.append(el.get_text(separator="\n", strip=True))
    return "\n\n".join(parts)


def _extract_indeed(soup: "BeautifulSoup") -> str:
    parts = []
    for sel in [
        "#jobDescriptionText",
        ".jobsearch-JobComponent",
        "[data-testid='jobsearch-jobDescriptionText']",
        ".jobsearch-JobInfoHeader-title",
    ]:
        el = soup.select_one(sel)
        if el:
            parts.append(el.get_text(separator="\n", strip=True))
    return "\n\n".join(parts)


def _extract_naukri(soup: "BeautifulSoup") -> str:
    parts = []
    for sel in [
        ".job-desc",
        ".jd-desc",
        "#job_description",
        ".styles_jhc__jd__m0A7X",
        ".dang-inner-html",
    ]:
        el = soup.select_one(sel)
        if el:
            parts.append(el.get_text(separator="\n", strip=True))
    return "\n\n".join(parts)


def _extract_glassdoor(soup: "BeautifulSoup") -> str:
    parts = []
    for sel in [
        "[data-test='jobDescriptionContent']",
        ".jobDescriptionContent",
        ".desc",
    ]:
        el = soup.select_one(sel)
        if el:
            parts.append(el.get_text(separator="\n", strip=True))
    return "\n\n".join(parts)


def _extract_generic(soup: "BeautifulSoup") -> str:
    """Generic extractor — removes boilerplate and extracts main content."""
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "advertisement", "cookie", "popup",
                     "iframe", "noscript"]):
        tag.decompose()
    # Try known content tags
    for sel in ["main", "article", "[role='main']", ".content", "#content",
                ".job-description", ".jd", "#job-desc", ".posting-requirements"]:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(separator="\n", strip=True)
            if len(txt) > 200:
                return txt
    # Fallback: full body
    body = soup.find("body")
    if body:
        text = body.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) > SCRAPE_MIN_LINE_LEN]
        return "\n".join(lines[:SCRAPE_MAX_LINES])
    return ""


def _domain_extractor(url: str, soup: "BeautifulSoup") -> str:
    """Route to domain-specific extractor."""
    domain = urlparse(url).netloc.lower()
    if "linkedin.com" in domain:
        result = _extract_linkedin(soup)
    elif "indeed.com" in domain:
        result = _extract_indeed(soup)
    elif "naukri.com" in domain:
        result = _extract_naukri(soup)
    elif "glassdoor.com" in domain:
        result = _extract_glassdoor(soup)
    else:
        result = _extract_generic(soup)
    # If domain-specific returned too little, fallback to generic
    if len(result.strip()) < 200:
        result = _extract_generic(soup)
    return result.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Core scraper
# ─────────────────────────────────────────────────────────────────────────────

def scrape_job_url(url: str) -> tuple[str, str]:
    """
    Scrape a job posting URL and return (text, error_message).
    error_message is "" on success, a description on failure.
    Tries multiple strategies:
      1. requests + BeautifulSoup (domain-aware)
      2. trafilatura (boilerplate-removal library)
      3. Proxy-less fetch with minimal headers
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if not REQUESTS_OK:
        return "", "requests library not installed. Run: pip install requests"
    if not BS4_OK:
        return "", "beautifulsoup4 not installed. Run: pip install beautifulsoup4"

    session = _build_session()
    domain = urlparse(url).netloc

    # ── Strategy 1: Full browser-like headers ─────────────────────────────────
    try:
        resp = session.get(url, headers=_headers(), timeout=SCRAPE_TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        text = _domain_extractor(url, soup)
        if len(text.strip()) > 300:
            return text, ""
    except Exception as e1:
        pass

    # ── Strategy 2: trafilatura (handles JS-heavy pages better) ───────────────
    if TRAFILATURA_OK:
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(
                    downloaded,
                    include_links=False,
                    include_images=False,
                    include_comments=False,
                    no_fallback=False,
                )
                if text and len(text.strip()) > 300:
                    return text.strip(), ""
        except Exception:
            pass

    # ── Strategy 3: Minimal headers fallback ──────────────────────────────────
    try:
        resp = session.get(
            url,
            headers={"User-Agent": _get_ua(), "Accept": "text/html"},
            timeout=SCRAPE_TIMEOUT,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        text = _extract_generic(soup)
        if len(text.strip()) > 100:
            return text, ""
    except Exception as e3:
        return "", f"All scraping strategies failed. Last error: {e3}"

    return "", "Could not extract meaningful content from the URL."


# ─────────────────────────────────────────────────────────────────────────────
# File parsers
# ─────────────────────────────────────────────────────────────────────────────

def parse_pdf(file_bytes: bytes) -> str:
    if not PDF_OK:
        return "[PDF libraries not installed – run: pip install pdfplumber PyPDF2]"
    text = ""
    try:
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception:
        try:
            reader = PyPDF2.PdfReader(BytesIO(file_bytes))
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
        except Exception as e:
            return f"[Error parsing PDF: {e}]"
    return text.strip()


def parse_docx(file_bytes: bytes) -> str:
    if not DOCX_OK:
        return "[python-docx not installed – run: pip install python-docx]"
    try:
        doc = DocxDocument(BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        return f"[Error parsing DOCX: {e}]"


def parse_job_file(uploaded_file) -> str:
    """Parse PDF / DOCX / TXT uploaded file and return text."""
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
    data = uploaded_file.read()
    if ext == "pdf":
        return parse_pdf(data)
    elif ext == "docx":
        return parse_docx(data)
    elif ext == "txt":
        return data.decode("utf-8", errors="ignore")
    return "[Unsupported file format. Use PDF, DOCX, or TXT]"


# ─────────────────────────────────────────────────────────────────────────────
# LLM-based job detail extraction
# ─────────────────────────────────────────────────────────────────────────────

def _groq_extract(raw_text: str) -> dict:
    """Call Groq LLM to extract structured job details from raw text."""
    if not GROQ_KEY:
        return _fallback_extract(raw_text)
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        system = (
            "You are a job description parser. Extract ALL available details "
            "from the text and return ONLY valid JSON, no markdown fences, no explanation."
        )
        schema = """{
  "title": "",
  "company": "",
  "location": "",
  "job_type": "",
  "salary": "",
  "experience": "",
  "education": "",
  "skills": [],
  "requirements": [],
  "responsibilities": [],
  "benefits": [],
  "deadline": "",
  "description": "",
  "apply_url": "",
  "posted_date": ""
}"""
        prompt = (
            f"Extract job details from this text into this exact JSON schema:\n{schema}\n\n"
            f"TEXT:\n{raw_text[:4000]}"
        )
        resp = client.chat.completions.create(
            model=MAIN_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2048,
            temperature=0.1,
        )
        raw_json = resp.choices[0].message.content.strip()
        raw_json = re.sub(r"```json|```", "", raw_json).strip()
        return json.loads(raw_json)
    except json.JSONDecodeError:
        return _fallback_extract(raw_text)
    except Exception:
        return _fallback_extract(raw_text)


def _fallback_extract(text: str) -> dict:
    """Regex-based fallback extractor when LLM fails."""
    title_match = re.search(
        r"(?:position|role|title|job title)[:\s]+([^\n]{5,80})", text, re.IGNORECASE
    )
    company_match = re.search(
        r"(?:company|employer|organization|at\s)[:\s]+([^\n]{3,60})", text, re.IGNORECASE
    )
    location_match = re.search(
        r"(?:location|based in|city)[:\s]+([^\n]{3,60})", text, re.IGNORECASE
    )
    salary_match = re.search(
        r"(?:salary|compensation|ctc|pay|lpa|₹|\$)[:\s]*([^\n]{3,50})", text, re.IGNORECASE
    )
    exp_match = re.search(
        r"(\d+[\+\-–]?\s*(?:to\s*\d+\s*)?years?\s*(?:of\s*)?(?:experience|exp))", text, re.IGNORECASE
    )
    # Extract bullet points as requirements
    bullets = re.findall(r"(?:^|\n)[•\-\*]\s*(.{10,120})", text)
    return {
        "title":            title_match.group(1).strip() if title_match else "Job Position",
        "company":          company_match.group(1).strip() if company_match else "",
        "location":         location_match.group(1).strip() if location_match else "",
        "job_type":         "",
        "salary":           salary_match.group(1).strip() if salary_match else "Not specified",
        "experience":       exp_match.group(1).strip() if exp_match else "",
        "education":        "",
        "skills":           [],
        "requirements":     bullets[:10],
        "responsibilities": [],
        "benefits":         [],
        "deadline":         "",
        "description":      text[:600],
        "apply_url":        "",
        "posted_date":      "",
    }


def extract_job_details(text: str) -> dict:
    """
    Main entry point: extract structured job details from raw text.
    Uses LLM first, falls back to regex.
    """
    if not text or len(text.strip()) < 20:
        return _fallback_extract("")
    return _groq_extract(text)


# ─────────────────────────────────────────────────────────────────────────────
# Agent-based full pipeline
# ─────────────────────────────────────────────────────────────────────────────

def extract_job_from_url(url: str) -> tuple[dict, str, str]:
    """
    Full pipeline: URL → scrape → LLM extract → structured dict.
    Returns (details_dict, raw_text, error_message).
    """
    raw_text, error = scrape_job_url(url)
    if error:
        return {}, "", error
    if not raw_text.strip():
        return {}, "", "No text could be extracted from that URL."
    details = extract_job_details(raw_text)
    return details, raw_text, ""


def extract_job_from_text(text: str) -> dict:
    """Pipeline: paste text → LLM extract → structured dict."""
    return extract_job_details(text)


def extract_job_from_file(uploaded_file) -> tuple[dict, str, str]:
    """Pipeline: uploaded file → parse → LLM extract → structured dict."""
    raw_text = parse_job_file(uploaded_file)
    if raw_text.startswith("["):
        return {}, "", raw_text
    details = extract_job_details(raw_text)
    return details, raw_text, ""