"""Test live AI prompt to see if Gemini actually works or fails."""
import os, sys
from pathlib import Path
from dotenv import load_dotenv

env_path = Path("D:/QC_Project/QC-Web/backend/.env")
load_dotenv(dotenv_path=env_path)

sys.path.insert(0, "D:/QC_Project/QC-Web/backend")
from app.ai.gemini_provider import GeminiProvider
from app.ai.openai_provider import OpenAIProvider

print("Testing Gemini live...")
gemini = GeminiProvider()
try:
    res = gemini.generate_test_cases({
        "url": "https://example.com",
        "name": "Example",
        "pages": [{"path": "/", "title": "Example Domain"}],
        "buttons": [{"text": "More information...", "type": "link", "page": "/"}],
        "inputs": [],
        "forms": [],
        "links": ["/more"]
    })
    print(f"Gemini SUCCESS: generated {len(res)} tests")
    for t in res[:2]:
        print(" -", t.get("name"))
except Exception as e:
    print(f"Gemini FAILED: {type(e).__name__}: {e}")

print("\nTesting OpenAI live...")
openai = OpenAIProvider()
try:
    res2 = openai.generate_test_cases({
        "url": "https://example.com",
        "name": "Example",
        "pages": [{"path": "/", "title": "Example Domain"}],
        "buttons": [{"text": "More information...", "type": "link", "page": "/"}],
        "inputs": [],
        "forms": [],
        "links": ["/more"]
    })
    print(f"OpenAI SUCCESS: generated {len(res2)} tests")
    for t in res2[:2]:
        print(" -", t.get("name"))
except Exception as e:
    print(f"OpenAI FAILED: {type(e).__name__}: {e}")
