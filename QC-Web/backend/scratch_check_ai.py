"""Scratch script to check AI provider status and readiness live."""
import sys
from pathlib import Path
from dotenv import load_dotenv

env_path = Path("D:/QC_Project/QC-Web/backend/.env")
print("Loading .env from:", env_path, "Exists:", env_path.exists())
load_dotenv(dotenv_path=env_path)

import os
print("AI_PROVIDER:", os.getenv("AI_PROVIDER"))
print("GEMINI_API_KEY set:", bool(os.getenv("GEMINI_API_KEY")))
print("OPENAI_API_KEY set:", bool(os.getenv("OPENAI_API_KEY")))

sys.path.insert(0, "D:/QC_Project/QC-Web/backend")
from app.ai.gemini_provider import GeminiProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.test_generation import get_ai_status

gemini = GeminiProvider()
print("Gemini is_configured:", gemini.is_configured())

openai = OpenAIProvider()
print("OpenAI is_configured:", openai.is_configured())

print("AI Status from test_generation:", get_ai_status())
