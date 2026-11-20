"""OpenAI Provider for Intelligent Regression Test Generation."""
import json
import logging
import os
import re
from typing import Any, Dict, List
from .provider import AIProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    """Generates regression test cases using OpenAI GPT-4o / GPT-4o-mini."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self._client = None
        if self.api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
                logger.info("OpenAIProvider initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
                self._client = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self._client)

    def get_name(self) -> str:
        return "openai"

    def generate_test_cases(self, app_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ask OpenAI to generate structured test cases based on real discovered DOM elements."""
        if not self.is_configured():
            raise RuntimeError("OpenAI API key is not configured.")

        prompt = self._build_prompt(app_context)
        try:
            response = self._client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert QA and Regression Test Engineer. Return ONLY valid JSON array."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            raw_text = response.choices[0].message.content.strip()
            data = json.loads(raw_text)
            if isinstance(data, dict):
                # Look for list in dict values
                for val in data.values():
                    if isinstance(val, list):
                        return val
            elif isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.error(f"OpenAI test generation failed: {e}")
            raise

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        target_url = context.get("url", "")
        pages = context.get("pages", [])
        buttons = context.get("buttons", [])
        inputs = context.get("inputs", [])
        forms = context.get("forms", [])
        links = context.get("links", [])
        focus_area = context.get("focus_area", "")

        focus_instruction = f" PRIMARY BATCH FOCUS: {focus_area}. Generate distinct regression tests specifically targeting this functional area." if focus_area else ""

        return f"""Analyze the real web application at {target_url} based on discovered DOM:{focus_instruction}

PAGES & ROUTES ({len(pages)}): {json.dumps(pages[:25], indent=2)}
BUTTONS & ACTIONS ({len(buttons)}): {json.dumps(buttons[:40], indent=2)}
INPUTS & CONTROLS ({len(inputs)}): {json.dumps(inputs[:25], indent=2)}
FORMS ({len(forms)}): {json.dumps(forms[:15], indent=2)}
LINKS ({len(links)}): {json.dumps(links[:30], indent=2)}

TASK:
Generate a comprehensive candidate regression test suite strictly based on these elements (aim for 4 to 8 distinct tests for this batch).
Cover different user journeys, states, inputs, and edge cases supported by the evidence. Do NOT invent elements or routes.
Do not generate redundant copies of "Verify Base URL Loads".

Return JSON with key "test_cases" containing an array of objects:
{{
  "test_cases": [
    {{
      "name": "...",
      "description": "...",
      "priority": "critical" | "high" | "medium" | "low",
      "target_route": "/...",
      "steps": ["..."],
      "expected_result": "...",
      "risk": 0.85,
      "coverage": 0.75,
      "execution_cost": 5.0,
      "redundancy_group": "auth" | "cart" | "search" | "checkout" | "nav" | null
    }}
  ]
}}
"""
