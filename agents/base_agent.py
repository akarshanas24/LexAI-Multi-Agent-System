import json

from config.settings import settings

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None

try:
    from anthropic import AsyncAnthropic
except Exception:  # pragma: no cover
    AsyncAnthropic = None


class BaseAgent:
    NAME = "Base Agent"
    SYSTEM_PROMPT = "You are a helpful legal reasoning assistant."

    def build_prompt(self, case: str, context: str = "") -> str:
        return f"{context}\n\n{case}".strip()

    async def run(self, prompt: str) -> str:
        ollama_response = await self._run_ollama(prompt)
        if ollama_response is not None:
            return ollama_response

        if settings.ANTHROPIC_API_KEY and AsyncAnthropic is not None:
            client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            response = await client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=800,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(
                block.text for block in response.content if getattr(block, "type", "") == "text"
            ).strip()
        return self._fallback_response(prompt)

    @classmethod
    def describe_backend(cls) -> dict[str, str]:
        if settings.OLLAMA_ENABLED and httpx is not None:
            return {
                "provider": "ollama",
                "model": settings.OLLAMA_MODEL,
                "endpoint": settings.OLLAMA_BASE_URL,
            }
        if settings.ANTHROPIC_API_KEY and AsyncAnthropic is not None:
            return {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-latest",
                "endpoint": "anthropic-api",
            }
        return {
            "provider": "fallback",
            "model": "local-placeholder",
            "endpoint": "none",
        }

    async def _run_ollama(self, prompt: str) -> str | None:
        if not settings.OLLAMA_ENABLED or httpx is None:
            return None

        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "system": self.SYSTEM_PROMPT,
            "stream": False,
            "options": {
                "temperature": 0.3,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
        except Exception:
            return None

        data = response.json()
        text = (data.get("response") or "").strip()
        return text or None

    def _fallback_response(self, prompt: str) -> str:
        return f"{self.NAME} placeholder response for: {prompt[:160]}"


def parse_json_response(raw: str, default: dict) -> dict:
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = default.copy()
    return parsed
