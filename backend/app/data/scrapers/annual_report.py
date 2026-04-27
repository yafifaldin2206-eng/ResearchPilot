"""Annual report scraper. Handles direct PDF URLs and IR landing pages."""
import re
from pathlib import Path
from typing import Optional
import httpx
import structlog
from playwright.async_api import async_playwright

from app.config import settings

logger = structlog.get_logger()

CACHE_DIR = Path("/tmp/researchpilot_cache")
CACHE_DIR.mkdir(exist_ok=True)


async def fetch_pdf(url: str, timeout: int = 60) -> bytes:
    """Download a PDF directly. Results are cached by URL hash."""
    import hashlib

    cache_key = hashlib.md5(url.encode()).hexdigest()
    cache_path = CACHE_DIR / f"{cache_key}.pdf"

    if cache_path.exists():
        logger.info("pdf_cache_hit", url=url)
        return cache_path.read_bytes()

    logger.info("pdf_fetching", url=url)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ResearchPilot/0.1)"},
        )
        response.raise_for_status()
        content = response.content

    cache_path.write_bytes(content)
    return content


async def fetch_via_browser(url: str) -> tuple[str, Optional[bytes]]:
    """
    For URLs that are not direct PDFs — open in a browser and find PDF links.
    Returns (html_content, pdf_bytes_if_found).
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=settings.SCRAPE_TIMEOUT * 1000)
            html = await page.content()

            pdf_links = await page.eval_on_selector_all(
                "a[href*='.pdf']",
                "els => els.map(e => e.href)",
            )

            if pdf_links:
                for pdf_url in pdf_links:
                    if any(kw in pdf_url.lower() for kw in ["annual", "report", "ar2", "ar-2"]):
                        pdf_bytes = await fetch_pdf(pdf_url)
                        return html, pdf_bytes

            return html, None
        finally:
            await browser.close()


async def get_annual_report_pdf(url: str) -> bytes:
    """
    Main entry point. Auto-detects whether the URL is a direct PDF or a landing page.
    """
    if url.lower().endswith(".pdf"):
        return await fetch_pdf(url)

    _, pdf = await fetch_via_browser(url)
    if pdf is None:
        raise ValueError(f"Could not find a PDF at {url}")
    return pdf
