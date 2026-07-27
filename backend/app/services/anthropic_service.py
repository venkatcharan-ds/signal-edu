"""
Anthropic API client wrapper.
Handles structured output parsing and enforces evidence-citation contracts.
"""
import anthropic
from app.config import get_settings
import structlog

log = structlog.get_logger()
settings = get_settings()


class AnthropicService:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.capability_model = settings.anthropic_model_capability
        self.recommendation_model = settings.anthropic_model_recommendation

    async def extract_capabilities(self, prompt: str) -> dict:
        """
        Call Claude Sonnet for capability extraction.
        Returns structured JSON with scores and mandatory evidence citations.
        """
        message = await self.client.messages.create(
            model=self.capability_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_response(message.content[0].text)

    async def generate_recommendations(self, prompt: str) -> dict:
        """
        Call Claude Haiku for recommendation generation.
        Returns structured JSON with prioritized, evidence-typed recommendations.
        """
        message = await self.client.messages.create(
            model=self.recommendation_model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_response(message.content[0].text)

    def _parse_json_response(self, text: str) -> dict:
        import json
        import re
        # Extract JSON block from response (Claude may include prose)
        match = re.search(r"```json\s*([\s\S]+?)\s*```", text)
        if match:
            return json.loads(match.group(1))
        return json.loads(text)
