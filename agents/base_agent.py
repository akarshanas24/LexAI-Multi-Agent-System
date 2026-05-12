import json

from config.settings import settings
from utils.logger import logger

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
        models_to_try: list[str] = []
        for model in (settings.OLLAMA_MODEL, *settings.OLLAMA_FALLBACK_MODELS):
            if model and model not in models_to_try:
                models_to_try.append(model)

        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
            for model_name in models_to_try:
                payload = {
                    "model": model_name,
                    "prompt": prompt,
                    "system": self.SYSTEM_PROMPT,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                    },
                }
                try:
                    response = await client.post(
                        f"{settings.OLLAMA_BASE_URL}/api/generate",
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                except Exception as exc:
                    logger.warning(
                        f"{self.NAME} Ollama request failed for model={model_name}: "
                        f"{type(exc).__name__}: {exc}"
                    )
                    continue

                text = (data.get("response") or "").strip()
                if text:
                    if model_name != settings.OLLAMA_MODEL:
                        logger.warning(
                            f"{self.NAME} fell back from model={settings.OLLAMA_MODEL} "
                            f"to model={model_name}"
                        )
                    return text

                logger.warning(f"{self.NAME} received an empty Ollama response for model={model_name}")

        return None

    @staticmethod
    def _prompt_preview(prompt: str, limit: int = 280) -> str:
        compact = " ".join(line.strip() for line in prompt.splitlines() if line.strip())
        if len(compact) <= limit:
            return compact
        cutoff = compact.rfind(" ", 0, limit)
        if cutoff < max(80, limit // 2):
            cutoff = limit
        return compact[:cutoff].rstrip(" ,;:") + "..."

    def _fallback_response(self, prompt: str) -> str:
        return (
            f"{self.NAME} is running in placeholder mode because no live LLM backend is available.\n\n"
            "Start Ollama or configure `ANTHROPIC_API_KEY` to generate a full response.\n\n"
            f"Prompt preview:\n{self._prompt_preview(prompt)}"
        )


def parse_json_response(raw: str, default: dict) -> dict:
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = default.copy()
    return parsed
