from __future__ import annotations
import json
import asyncio
from typing import Any, Optional
from openai import AsyncOpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, VISION_MODEL, REASONING_MODEL


_client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
)

_EXTRA_HEADERS = {
    "HTTP-Referer": "https://plum-claims.local",
    "X-Title": "Plum Claims Processor",
}


async def chat(
    messages: list[dict],
    model: str = REASONING_MODEL,
    temperature: float = 0.1,
    max_tokens: int = 2048,
    retries: int = 2,
    timeout: float = 30.0,
) -> str:
    for attempt in range(retries + 1):
        try:
            response = await asyncio.wait_for(
                _client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    extra_headers=_EXTRA_HEADERS,
                ),
                timeout=timeout,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            if attempt == retries:
                raise
            await asyncio.sleep(1.5 ** attempt)
    return ""


async def vision_chat(
    prompt: str,
    image_b64: Optional[str] = None,
    mime_type: str = "image/jpeg",
    model: str = VISION_MODEL,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    content: list[dict] = [{"type": "text", "text": prompt}]
    if image_b64:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
        })
    return await chat(
        messages=[{"role": "user", "content": content}],
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def parse_json_response(text: str) -> Any:
    """Extract JSON from LLM response, stripping markdown fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object/array in the text
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            start = text.find(start_char)
            end = text.rfind(end_char)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    continue
        raise ValueError(f"Could not parse JSON from: {text[:200]}")
