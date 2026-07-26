"""Connectors to the three public data sources Lumen can read.

Each connector takes the parameters produced by the router, performs the HTTP
call(s), records what it did in the tracer, and returns a small, tidy dict that
is easy for both Gemini and the offline templates to describe.

None of these APIs require an API key.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests

from . import config
from .trace import Tracer


class SourceError(Exception):
    """A friendly, expected problem (city not found, unknown coin, ...)."""


_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": config.USER_AGENT})


def _get(url: str, tracer: Tracer, accept_json: bool = True, params: Optional[dict] = None) -> Any:
    """GET a URL, record the call, and return parsed JSON."""
    start = time.perf_counter()
    resp = _SESSION.get(url, params=params, timeout=config.HTTP_TIMEOUT)
    ms = (time.perf_counter() - start) * 1000.0
    shown = resp.url if len(resp.url) <= 88 else resp.url[:88] + "…"
    tracer.add("http", f"GET → HTTP {resp.status_code}", shown, ms=ms)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json() if accept_json else resp.text


# --------------------------------------------------------------------------
#  1) WEATHER  —  wttr.in  (returns JSON with ?format=j1)
# --------------------------------------------------------------------------
def weather(params: Dict[str, str], tracer: Tracer) -> Dict[str, Any]:
    city = (params.get("city") or params.get("location") or "Tashkent").strip()
    data = _get(f"https://wttr.in/{requests.utils.quote(city)}", tracer, params={"format": "j1"})
    if not data or not data.get("current_condition"):
        raise SourceError(f'I could not find weather for "{city}".')

    cur = data["current_condition"][0]
    area = (data.get("nearest_area") or [{}])[0]

    def _first(node: Any) -> str:
        if isinstance(node, list) and node:
            return str(node[0].get("value", "")).strip()
        return ""

    place = ", ".join(
        p for p in (_first(area.get("areaName")), _first(area.get("country"))) if p
    )
    return {
        "place": place or city,
        "temperature_c": cur.get("temp_C"),
        "feels_like_c": cur.get("FeelsLikeC"),
        "description": _first(cur.get("weatherDesc")),
        "humidity_pct": cur.get("humidity"),
        "wind_kmph": cur.get("windspeedKmph"),
        "observation_time": cur.get("observation_time"),
    }


# --------------------------------------------------------------------------
#  2) GITHUB  —  official REST API
# --------------------------------------------------------------------------
def github(params: Dict[str, str], tracer: Tracer) -> Dict[str, Any]:
    owner = (params.get("owner") or "").strip()
    repo = (params.get("repo") or "").strip()

    if owner and repo:
        data = _get(f"https://api.github.com/repos/{owner}/{repo}", tracer)
        if not data:
            raise SourceError(f'I could not find the repository "{owner}/{repo}".')
        return {
            "type": "repository",
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "language": data.get("language"),
            "stars": data.get("stargazers_count"),
            "forks": data.get("forks_count"),
            "open_issues": data.get("open_issues_count"),
            "topics": data.get("topics"),
            "url": data.get("html_url"),
        }

    login = (params.get("user") or params.get("username") or params.get("org") or "github").strip()
    data = _get(f"https://api.github.com/users/{login}", tracer)
    if not data:
        raise SourceError(f'I could not find a GitHub account called "{login}".')
    return {
        "type": "account",
        "login": data.get("login"),
        "name": data.get("name"),
        "account_kind": (data.get("type") or "user").lower(),
        "bio": data.get("bio"),
        "company": data.get("company"),
        "location": data.get("location"),
        "public_repos": data.get("public_repos"),
        "followers": data.get("followers"),
        "following": data.get("following"),
        "url": data.get("html_url"),
    }


# --------------------------------------------------------------------------
#  3) CRYPTO PRICES  —  CoinGecko
# --------------------------------------------------------------------------
_COIN_ALIASES = {
    "btc": "bitcoin",
    "bitcoin": "bitcoin",
    "eth": "ethereum",
    "ether": "ethereum",
    "ethereum": "ethereum",
    "sol": "solana",
    "solana": "solana",
    "doge": "dogecoin",
    "dogecoin": "dogecoin",
    "ada": "cardano",
    "cardano": "cardano",
    "xrp": "ripple",
    "bnb": "binancecoin",
    "ton": "the-open-network",
}


def _resolve_coin_id(name: str, tracer: Tracer) -> Optional[str]:
    key = name.lower().strip()
    if key in _COIN_ALIASES:
        return _COIN_ALIASES[key]
    # Fall back to CoinGecko's search to resolve an arbitrary name.
    data = _get("https://api.coingecko.com/api/v3/search", tracer, params={"query": name})
    coins = (data or {}).get("coins") or []
    return coins[0]["id"] if coins else None


def crypto(params: Dict[str, str], tracer: Tracer) -> Dict[str, Any]:
    name = (params.get("coin") or params.get("id") or params.get("symbol") or "bitcoin").strip()
    vs = (params.get("vs") or params.get("currency") or "usd").lower().strip()

    coin_id = _resolve_coin_id(name, tracer)
    if not coin_id:
        raise SourceError(f'I could not find a coin called "{name}".')

    data = _get(
        "https://api.coingecko.com/api/v3/simple/price",
        tracer,
        params={
            "ids": coin_id,
            "vs_currencies": vs,
            "include_market_cap": "true",
            "include_24hr_change": "true",
            "include_last_updated_at": "true",
        },
    )
    row = (data or {}).get(coin_id)
    if not row or row.get(vs) is None:
        raise SourceError(f'I could not get a {vs.upper()} price for "{name}".')

    return {
        "coin": coin_id,
        "vs_currency": vs.upper(),
        "price": row.get(vs),
        "market_cap": row.get(f"{vs}_market_cap"),
        "change_24h_pct": row.get(f"{vs}_24h_change"),
    }
