"""
Precedent Search workflow.

Finds analogous deals, strategic moves, or business model precedents.
Most useful for: M&A comps, fundraising analogues, market entry precedents.

Usage:
    result = await run("B2B stablecoin payments infrastructure Southeast Asia Series A")
    result = await run("cloud kitchen operator IPO")
    result = await run("vertical SaaS acquiring payment license Indonesia")
"""
import structlog
from typing import Callable, Optional, Awaitable

from app.data.search import search_company_context
from app.llm.client import complete
from app.llm.validators import validate_citations

logger = structlog.get_logger()

ProgressCallback = Callable[[str, int, Optional[dict]], Awaitable[None]]

PRECEDENT_SYSTEM = """You are a senior strategy consultant specializing in precedent analysis for M&A, fundraising, and strategic decisions.

Your task: Find 5-8 relevant precedents for the given scenario.

For each precedent:

**[Company/Deal Name]** ([Year]) — [Geography]
- What happened: 1-2 sentences
- Scale/context: revenue, valuation, or deal size at the time
- Why it is analogous: specific parallels to the query
- Outcome: what happened next (success, failure, pivot)
- Key lesson: the single most actionable insight

Then:

## Pattern synthesis
What do these precedents have in common? What does that imply for the query?

## Cautionary cases
1-2 precedents where similar situations went badly wrong, and why.

## Confidence note
Be explicit about which precedents are strong analogues vs loose ones.

SOURCE RULES: Cite with [Source: URL] for every deal/company fact. Never fabricate valuations."""

PRECEDENT_USER = """Find precedents for: {target}

Research gathered:
---
{research_data}
---

Generate precedent analysis."""


async def _noop(step: str, pct: int, detail: Optional[dict] = None) -> None:
    pass


async def run(target: str, progress: ProgressCallback = _noop) -> dict:
    """
    Find strategic, M&A, or fundraising precedents.

    Args:
        target: Scenario description, e.g., "stablecoin B2B payments startup Series A SEA"
    """
    await progress("scoping", 10, {"message": f"Searching precedents for: {target}..."})

    results_main = await search_company_context(target, max_results=6)
    results_deals = await search_company_context(f"{target} acquisition funding deal", max_results=4)

    all_results = {r["url"]: r for r in results_main + results_deals}.values()
    research_data = "\n\n---\n\n".join(
        f"Source: {r['url']}\nTitle: {r['title']}\n\n{r['text'][:2500]}"
        for r in list(all_results)[:10]
    )

    await progress("analyzing", 55, {"message": "Synthesizing precedents..."})

    analysis = await complete(
        system=PRECEDENT_SYSTEM,
        user=PRECEDENT_USER.format(target=target, research_data=research_data),
        max_tokens=5000,
        temperature=0.3,
    )

    await progress("validating", 90, None)
    validation = validate_citations(analysis, min_citation_ratio=0.25)

    await progress("done", 100, {"valid": validation.is_valid})

    return {
        "analysis": analysis,
        "target": target,
        "validation": {
            "is_valid": validation.is_valid,
            "citation_count": validation.citation_count,
            "issues": validation.issues[:5],
        },
        "sources": [r["url"] for r in all_results],
    }
