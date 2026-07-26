"""Step 1 of the pipeline: decide WHICH source answers the question.

Preferred path: ask Gemini to emit strict JSON naming the source + parameters.
Backup path: a deterministic keyword matcher, so the whole pipeline still works
with no API key and no internet round-trip to the model.
"""
from __future__ import annotations

import json
import re
from typing import Dict

from .llm import GeminiClient, LLMError, strip_code_fences
from .trace import Tracer

VALID_SOURCES = ("weather", "github", "crypto", "none")

_PROMPT = """You route questions to ONE data source and pull out its parameters.

Available sources and the exact parameter keys each expects:
- weather : {{ "city": "<city name>" }}
- github  : {{ "owner": "<owner>", "repo": "<repo>" }}   for a specific repository
            or {{ "user": "<login>" }}                    for a user or organisation
- crypto  : {{ "coin": "<coin name or ticker>", "vs": "<fiat code, default usd>" }}
- none    : {{ }}   when nothing above fits

Return STRICT JSON only, no prose, no code fences:
{{"source": "<one of weather|github|crypto|none>", "params": {{ ... }}}}

Question: "{question}"
"""


def _coerce(obj: object) -> Dict[str, object]:
    if not isinstance(obj, dict):
        return {"source": "none", "params": {}}
    source = obj.get("source")
    if source not in VALID_SOURCES:
        source = "none"
    params = obj.get("params")
    if not isinstance(params, dict):
        params = {}
    # Normalise all param values to plain strings.
    params = {str(k): ("" if v is None else str(v)) for k, v in params.items()}
    return {"source": source, "params": params}


def route(question: str, llm: GeminiClient, tracer: Tracer) -> Dict[str, object]:
    """Return {"source": ..., "params": {...}, "mode": "ai"|"offline"}."""
    if llm.available:
        tracer.add("router", "Routing with Gemini", "asking the model to pick a source")
        try:
            raw = llm.generate(_PROMPT.format(question=question), tracer, json_mode=True)
            parsed = _coerce(json.loads(strip_code_fences(raw)))
            parsed["mode"] = "ai"
            tracer.add("router", "Source chosen", f'{parsed["source"]}  {parsed["params"]}')
            return parsed
        except (LLMError, json.JSONDecodeError, ValueError) as err:
            tracer.add("fallback", "Gemini routing failed", f"{err} — using keyword rules")

    else:
        tracer.add("fallback", "No Gemini key", "using keyword rules to route")

    parsed = keyword_route(question)
    parsed["mode"] = "offline"
    tracer.add("router", "Source chosen (offline)", f'{parsed["source"]}  {parsed["params"]}')
    return parsed


# --------------------------------------------------------------------------
#  Deterministic backup router
# --------------------------------------------------------------------------
_COIN_WORDS = (
    "bitcoin", "btc", "ethereum", "eth", "solana", "sol", "dogecoin", "doge",
    "cardano", "ada", "ripple", "xrp", "binancecoin", "bnb", "ton", "crypto",
    "coin", "token",
)


def keyword_route(question: str) -> Dict[str, object]:
    q = question.lower().strip()

    # crypto ---------------------------------------------------------------
    if any(w in q for w in _COIN_WORDS) or re.search(r"\bprice of\b", q):
        m = re.search(r"(?:price of|worth of|value of|of)\s+([a-z][a-z0-9 .-]*)", q)
        coin = ""
        if m:
            coin = m.group(1).strip()
        if not coin:
            for w in _COIN_WORDS:
                if w in q and w not in ("crypto", "coin", "token", "price"):
                    coin = w
                    break
        return {"source": "crypto", "params": {"coin": coin or "bitcoin", "vs": "usd"}}

    # weather --------------------------------------------------------------
    if re.search(r"\b(weather|temperature|forecast|rain|hot|cold|climate)\b", q):
        m = re.search(r"\b(?:in|at|for)\s+([a-zà-ÿ' .-]+)$", q)
        city = (m.group(1) if m else re.sub(r".*weather\s*(in|at|for)?", "", q)).strip(" ?.!")
        return {"source": "weather", "params": {"city": city or "Tashkent"}}

    # github ---------------------------------------------------------------
    repo = re.search(r"\b([a-z0-9][a-z0-9-]+)/([a-z0-9._-]+)", question, re.I)
    if repo:
        return {"source": "github", "params": {"owner": repo.group(1), "repo": repo.group(2)}}
    if "github" in q:
        m = re.search(r"\b(?:about|user|for|of)\s+([a-z0-9-]+)", q)
        return {"source": "github", "params": {"user": m.group(1) if m else "github"}}

    return {"source": "none", "params": {}}
