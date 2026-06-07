from __future__ import annotations
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./claims.db")

# Models — gemini-2.5-flash for vision, deepseek-chat-v3 for reasoning
VISION_MODEL = "google/gemini-2.5-flash"
REASONING_MODEL = "deepseek/deepseek-chat-v3-0324"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_policy_path = Path(os.getenv("POLICY_FILE", "../policy_terms.json"))
if not _policy_path.exists():
    _policy_path = Path(__file__).parent.parent / "policy_terms.json"

with open(_policy_path, encoding="utf-8") as _f:
    POLICY: dict = json.load(_f)
