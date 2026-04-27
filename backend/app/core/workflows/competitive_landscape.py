"""
Competitive Landscape workflow.

Steps:
1. Exa search for top competitors and market sizing
2. Fetch overview pages for each competitor
3. Synthesize competitive map with positioning

Usage:
    from app.core.workflows.competitive_landscape import run
    result = await run("Southeast Asia cloud kitchen market")
"""
import structlog
from typing import Callable, Optional, Awaitable

from app.data.search import search_company_context
from app.llm.client import complete
from app.llm.validators import validate_citations

logger = structlog.get_logger()

ProgressCallback = Callable[[str, int, Optional[dict]], Awaitable[None]]


LANDSCAPE_SYSTEM = """You are a senior strategy consultant building competitive intelligence maps.

Output a competitive landscape analysis. Structure:

## Market Overview
- Market size and growth rate (cite source)
- Key value chain stages
- Major tailwinds and headwinds

## Competitor Profiles
For each of the top 5-7 competitors:
**[Company Name]** — [one-line positioning]
- Business model: how they make money
- Scale: revenue/GMV/users if known
- Differentiation: what they claim to do better
- Weakness: notable gaps or vulnerabilities

## Positioning Map
Describe where each player sits on 2 key axes (pick the most strategic axes for this market, e.g., price vs quality, scale vs specialization, tech vs relationship-driven).

## White Space
3-5 market positions no current player occupies well.

## Competitive Intensity Verdict
One of: Fragmented | Consolidating | Duopoly | Monopoly — and why.

CITATION RULES: cite every factual claim with [Source: URL] or [Source: Company Name website/report].
Do NOT fabricate revenue figures. Use "not publicly disclosed" if unknown."""

LANDSCAPE_USER = """Market/Industry to map: {target}

Research data from web:
---
{research_data}
---

Generate competitive landscape analysis."""


async def _noop(step: str, pct: int, detail: Optional[dict] = None) -> None:
    pass


async def run(target: str, progress: ProgressCallback = _noop) -> dict:
    """
    Run competitive landscape analysis.

    Args:
        target: Market or company context, e.g., "Indonesian B2B payments" or "Tokopedia competitors"
    """
    await progress("scoping", 10, {"message": f"Researching {target}..."})

    results = await search_company_context(target, max_results=8)
    research_data = "\n\n---\n\n".join(
        f"Source: {r['url']}\nTitle: {r['title']}\n\n{r['text'][:3000]}"
        for r in results
    )

    await progress("analyzing", 50, {"message": "Building competitive map..."})

    analysis = await complete(
        system=LANDSCAPE_SYSTEM,
        user=LANDSCAPE_USER.format(target=target, research_data=research_data),
        max_tokens=6000,
        temperature=0.3,
    )

    await progress("validating", 90, None)
    validation = validate_citations(analysis, min_citation_ratio=0.3)

    await progress("done", 100, {"valid": validation.is_valid})

    return {
        "analysis": analysis,
        "target": target,
        "validation": {
            "is_valid": validation.is_valid,
            "citation_count": validation.citation_count,
            "issues": validation.issues[:5],
        },
        "sources": [r["url"] for r in results],
    }
