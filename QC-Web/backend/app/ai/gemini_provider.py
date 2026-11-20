"""Google Gemini AI Provider for Intelligent Regression Test Generation."""

import json
import logging
import os
import re
from typing import Any, Dict, List

from google import genai
from google.genai import types

from .provider import AIProvider

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    """Generates regression test cases using Google Gemini."""

    MODELS = [
        "gemini-3.5-flash-lite",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
    ]

    def __init__(self):
        self.api_key = (
            os.getenv("GEMINI_API_KEY", "")
            or os.getenv("GOOGLE_API_KEY", "")
        ).strip()

        self._client = None

        if self.api_key:
            try:
                self._client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(
                        timeout=60000
                    ),
                )

                logger.info(
                    "GeminiProvider initialized successfully.",
                )

            except Exception as e:
                logger.exception(
                    "Failed to initialize Gemini client: %s",
                    e,
                )
                self._client = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self._client)

    def get_name(self) -> str:
        return "gemini"

    def generate_test_cases(
        self,
        app_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:

        if not self.is_configured():
            raise RuntimeError(
                "Gemini API key is not configured."
            )

        prompt = self._build_prompt(app_context)

        last_error = None
        raw_text = ""
        for model_name in self.MODELS:
            logger.info("Attempting test generation with Gemini model %s...", model_name)
            try:
                response = self._client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                        max_output_tokens=8000,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=True
                        ),
                    ),
                )
                raw_text = (response.text or "").strip()
                if raw_text:
                    logger.info("Gemini model %s succeeded, returned %d chars.", model_name, len(raw_text))
                    break
            except Exception as exc:
                logger.warning("Gemini model %s encountered error: %s. Trying next model...", model_name, exc)
                last_error = exc
        else:
            raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")

        if not raw_text:
            raise RuntimeError("Gemini returned an empty response.")

        logger.info("Gemini returned %d characters.", len(raw_text))

        # Remove markdown code fences if Gemini adds them
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
            raw_text = re.sub(r"\s*```$", "", raw_text)

        try:
            data = json.loads(raw_text)
        except Exception as json_err:
            raise RuntimeError(f"Failed to parse Gemini response as JSON: {json_err}")

        if isinstance(data, dict) and "test_cases" in data:
            test_cases = data["test_cases"]
        elif isinstance(data, list):
            test_cases = data
        else:
            raise RuntimeError("Gemini returned an unexpected JSON structure.")

        if not isinstance(test_cases, list):
            raise RuntimeError("Gemini test_cases value is not a list.")

        logger.info("Gemini generated %d candidate test cases.", len(test_cases))
        return test_cases

    def _build_prompt(
        self,
        context: Dict[str, Any]
    ) -> str:

        target_url = context.get("url", "")
        pages = context.get("pages", [])
        buttons = context.get("buttons", [])
        inputs = context.get("inputs", [])
        forms = context.get("forms", [])
        links = context.get("links", [])
        focus_area = context.get("focus_area", "")

        focus_header = f"""
======================================================
PRIMARY FOCUS AREA FOR THIS GENERATION BATCH:
{focus_area}
======================================================
Generate regression candidates specifically addressing this focus area using the discovered elements.
""" if focus_area else ""

        return f"""
You are an expert QA and regression test engineer.

You are analyzing a REAL web application.

TARGET URL:
{target_url}
{focus_header}

The following information was discovered dynamically from the website using Playwright:

PAGES & ROUTES DISCOVERED ({len(pages)}):
{json.dumps(pages[:25], indent=2, ensure_ascii=False)}

INTERACTIVE BUTTONS & ACTIONS ({len(buttons)}):
{json.dumps(buttons[:40], indent=2, ensure_ascii=False)}

INPUT FIELDS & CONTROLS ({len(inputs)}):
{json.dumps(inputs[:25], indent=2, ensure_ascii=False)}

FORMS ({len(forms)}):
{json.dumps(forms[:15], indent=2, ensure_ascii=False)}

SAME-ORIGIN LINKS ({len(links)}):
{json.dumps(links[:30], indent=2, ensure_ascii=False)}

TASK:
Generate functional and edge-case regression test cases ONLY for functionality actually observed in the discovered website.

CRITICAL CANDIDATE SUITE REQUIREMENTS:
1. COMPREHENSIVE SUITE: Generate ALL meaningful distinct regression candidates supported by the evidence (aim for 4 to 8 high-quality tests for this batch). Do NOT stop after 1 or 2 examples.
2. DIVERSE WORKFLOWS: Cover different user journeys, positive interactions, valid user states, and input/edge scenarios where supported by the elements.
3. GROUNDED IN EVIDENCE: Do NOT invent pages, buttons, forms, products, workflows, routes, or functionality that were not discovered. Every step must reference observed routes and elements.
4. ROOT SMOKE LIMIT: Do NOT generate multiple trivial variations of "Verify Base URL Loads" or "Verify homepage loads". If a root load test is appropriate, include at most ONE. All other tests must verify specific routes, buttons, inputs, searches, or actions.
5. EXECUTABLE: Tests must be realistically executable through Playwright against the target URL.
6. VALID JSON ONLY: Return strictly valid JSON matching the schema below. No markdown fences.

Return:
{{
  "test_cases": [
    {{
      "name": "Concise descriptive test name",
      "description": "What functionality is being verified",
      "priority": "critical",
      "target_route": "/path",
      "steps": [
        "Navigate to ...",
        "Interact with ...",
        "Verify ..."
      ],
      "expected_result": "Expected observable result",
      "risk": 0.85,
      "coverage": 0.75,
      "execution_cost": 5.0,
      "redundancy_group": "functional-area"
    }}
  ]
}}

Allowed priority values: critical, high, medium, low.
risk: 0.0 to 1.0 (higher = more critical/risky failure impact).
coverage: 0.0 to 1.0 (higher = wider surface coverage).
execution_cost: estimated duration in seconds (typically 3.0 to 15.0).
"""