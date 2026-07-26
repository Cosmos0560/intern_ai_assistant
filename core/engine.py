"""The orchestrator that ties the three steps together.

    question -> route -> fetch -> respond -> result(+trace)

An Engine instance is created once and shared across web requests. It owns the
Gemini client (so the call counter is session-wide) and a small answer cache.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from . import config, connectors
from .llm import GeminiClient
from .responder import respond
from .router import route
from .trace import Tracer

_FETCHERS = {
    "weather": connectors.weather,
    "github": connectors.github,
    "crypto": connectors.crypto,
}


class Engine:
    def __init__(self) -> None:
        self.llm = GeminiClient()
        self._cache: Dict[str, Dict[str, Any]] = {}

    # -- public API -----------------------------------------------------
    def status(self) -> Dict[str, Any]:
        return {
            "has_key": config.HAS_KEY,
            "model": config.GEMINI_MODEL,
            "gemini_calls": self.llm.calls,
        }

    def ask(self, question: str) -> Dict[str, Any]:
        question = (question or "").strip()[:500]
        tracer = Tracer()

        if not question:
            return self._package(tracer, answer="Please type a question first.",
                                 source="none", params={}, mode="offline", raw=None)

        tracer.add("router", "Question received", question)

        # 1) cache -------------------------------------------------------
        key = " ".join(question.lower().split())
        cached = self._cache.get(key)
        if cached and (time.time() - cached["_at"] < config.CACHE_TTL_SECONDS):
            tracer.add("cache", "Cache hit", "served without calling Gemini again")
            out = dict(cached["payload"])
            out["cached"] = True
            out["trace"] = tracer.as_list()
            out["gemini_calls"] = self.llm.calls
            return out

        # 2) route -------------------------------------------------------
        decision = route(question, self.llm, tracer)
        source = decision["source"]
        params = decision["params"]
        route_mode = decision["mode"]

        if source == "none":
            return self._package(
                tracer, answer=respond_none(), source="none",
                params=params, mode=route_mode, raw=None, store_key=key,
            )

        # 3) fetch -------------------------------------------------------
        try:
            raw = _FETCHERS[source](params, tracer)
        except connectors.SourceError as err:
            tracer.add("notice", "Nothing to summarise", str(err))
            return self._package(
                tracer, answer=str(err), source=source, params=params,
                mode="offline", raw=None, store_key=None,  # don't cache misses
            )

        # 4) respond -----------------------------------------------------
        # If routing already fell back to offline, keep the answer offline too
        # so a single question never mixes "no model" with a surprise call.
        answer, answer_mode = respond(
            question, source, raw, self.llm, tracer, prefer_offline=(route_mode == "offline")
        )
        mode = "ai" if (route_mode == "ai" and answer_mode == "ai") else "offline"

        return self._package(
            tracer, answer=answer, source=source, params=params,
            mode=mode, raw=raw, store_key=key,
        )

    # -- helpers --------------------------------------------------------
    def _package(
        self,
        tracer: Tracer,
        *,
        answer: str,
        source: str,
        params: Dict[str, Any],
        mode: str,
        raw: Any,
        store_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        tracer.add("notice", "Answer ready", "")
        payload = {
            "answer": answer,
            "source": source,
            "params": params,
            "mode": mode,
            "raw": raw,
            "cached": False,
        }
        if store_key:
            self._cache[store_key] = {"_at": time.time(), "payload": dict(payload)}
        payload["trace"] = tracer.as_list()
        payload["gemini_calls"] = self.llm.calls
        return payload


def respond_none() -> str:
    return (
        "I could not match that to a data source I know. Try asking about the weather "
        "in a city, a GitHub user or repository, or the price of a cryptocurrency."
    )
