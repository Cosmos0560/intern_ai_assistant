"""Step 3 of the pipeline: turn fetched JSON into a short, human answer.

Preferred path: hand the raw data to Gemini and ask for a 2-3 sentence summary
that uses ONLY that data. Backup path: deterministic templates, one per source,
so an answer always comes out even without the model.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from .llm import GeminiClient, LLMError
from .trace import Tracer

_PROMPT = """A user asked: "{question}"

Here is the real JSON data Lumen fetched from the {source} source:
{data}

Write a friendly answer of 2 to 3 sentences in plain English.
Rules: use only the data above, never invent facts, put the direct answer first,
and include units where they apply. Do not use markdown headings or bullet lists.
"""


def respond(
    question: str,
    source: str,
    data: Dict[str, Any],
    llm: GeminiClient,
    tracer: Tracer,
    prefer_offline: bool,
) -> Tuple[str, str]:
    """Return (answer_text, mode) where mode is "ai" or "offline"."""
    if llm.available and not prefer_offline:
        tracer.add("llm", "Summarising with Gemini", "turning raw data into a sentence")
        try:
            import json

            text = llm.generate(
                _PROMPT.format(question=question, source=source, data=json.dumps(data, indent=2)),
                tracer,
            )
            return text, "ai"
        except LLMError as err:
            tracer.add("fallback", "Gemini summary failed", f"{err} — using template")

    tracer.add("fallback", "Local template answer", "composed without the model")
    return _template(source, data), "offline"


def _n(value: Any) -> str:
    """Format an integer-ish value with thousands separators, else '?'."""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "?" if value is None else str(value)


def _template(source: str, d: Dict[str, Any]) -> str:
    if source == "weather":
        feels = f" (feels like {d.get('feels_like_c')}°C)" if d.get("feels_like_c") else ""
        return (
            f"It is {d.get('temperature_c')}°C{feels} in {d.get('place')} right now, "
            f"with {d.get('description', 'no description').lower()}. "
            f"Humidity is {d.get('humidity_pct')}% and wind is about {d.get('wind_kmph')} km/h."
        )

    if source == "github":
        if d.get("type") == "repository":
            desc = d.get("description") or "no description provided"
            lang = f", mostly written in {d['language']}" if d.get("language") else ""
            return (
                f"{d.get('full_name')} — {desc.rstrip('.')}. "
                f"It has {_n(d.get('stars'))} stars and {_n(d.get('forks'))} forks{lang}. "
                f"Repository: {d.get('url')}"
            )
        name = d.get("name") or d.get("login")
        bio = f" — {d['bio'].rstrip('.')}" if d.get("bio") else ""
        return (
            f"{name} (@{d.get('login')}) is a GitHub {d.get('account_kind', 'account')}{bio}. "
            f"The account has {_n(d.get('public_repos'))} public repositories and "
            f"{_n(d.get('followers'))} followers. Profile: {d.get('url')}"
        )

    if source == "crypto":
        change = d.get("change_24h_pct")
        change_txt = ""
        if isinstance(change, (int, float)):
            arrow = "up" if change >= 0 else "down"
            change_txt = f" It is {arrow} {abs(change):.2f}% over the last 24 hours."
        cap = d.get("market_cap")
        cap_txt = f" Market cap is about {int(cap):,} {d.get('vs_currency')}." if cap else ""
        return (
            f"One {d.get('coin')} is worth about {d.get('price')} {d.get('vs_currency')} right now."
            f"{change_txt}{cap_txt}"
        )

    return (
        "I could not match that to a data source I know. Try asking about the weather "
        "in a city, a GitHub user or repository, or the price of a cryptocurrency."
    )
