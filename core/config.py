"""Central configuration for Lumen.

Every tunable lives here so the rest of the code never reads os.environ
directly. Values come from the process environment, optionally loaded from a
local .env file (see .env.example).
"""
from __future__ import annotations

import os

try:
    # Optional: load a .env file if python-dotenv is installed.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is a convenience, not a requirement
    pass


def _flag(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


# --- Language model -------------------------------------------------------
# Lumen talks to Google Gemini. Only the model name and key live here; the
# actual client is built in core/llm.py.
#
# The homework brief named "gemini-2.5-flash-lite". If Google retires it for
# your key, just set GEMINI_MODEL in your .env to any current free-tier model
# and nothing else has to change.
GEMINI_MODEL = _flag("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_API_KEY = _flag("GEMINI_API_KEY")
HAS_KEY = bool(GEMINI_API_KEY)

# --- HTTP behaviour -------------------------------------------------------
HTTP_TIMEOUT = float(_flag("HTTP_TIMEOUT", "12"))
USER_AGENT = "Lumen/1.0 (natural-language data assistant)"

# --- Rate-limit handling --------------------------------------------------
# The free Gemini tier is generous but finite. When it answers "429 / quota",
# we wait and retry a couple of times before giving up and going offline.
LLM_MAX_ATTEMPTS = 3
LLM_BACKOFF_SECONDS = 2.0  # 2s, 4s, ...

# --- Answer cache ---------------------------------------------------------
# Repeating a question during a demo should not burn quota, so identical
# questions are served from memory for a while.
CACHE_TTL_SECONDS = 600  # 10 minutes

# --- Web server -----------------------------------------------------------
HOST = _flag("HOST", "127.0.0.1")
PORT = int(_flag("PORT", "5000"))
