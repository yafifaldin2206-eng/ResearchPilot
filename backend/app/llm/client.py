"""Claude client wrapper with retry and streaming support."""
from typing import AsyncIterator, Optional
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from app.config import settings

logger = structlog.get_logger()

_client: Optional[AsyncAnthropic] = None


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
async def complete(
    system: str,
    user: str,
    max_tokens: Optional[int] = None,
    temperature: float = 0.3,
) -> str:
    """Single-turn completion. Use for discrete tasks."""
    client = get_client()
    response = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=max_tokens or settings.CLAUDE_MAX_TOKENS,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


async def stream(
    system: str,
    user: str,
    max_tokens: Optional[int] = None,
    temperature: float = 0.3,
) -> AsyncIterator[str]:
    """Streaming completion for real-time UI feedback."""
    client = get_client()
    async with client.messages.stream(
        model=settings.CLAUDE_MODEL,
        max_tokens=max_tokens or settings.CLAUDE_MAX_TOKENS,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
