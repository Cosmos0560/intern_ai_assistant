"""Thin wrapper around Google Gemini.

Design goals:
  * The rest of the app should not care whether the SDK is installed or a key
    is present. It just asks `client.available` and calls `client.generate(...)`.
  * A rate-limit ("429 / quota exhausted") is retried with exponential backoff.
  * Any other failure raises LLMError so the caller can fall back to local logic.
"""
from __future__ import annotations

import time

from . import config
from .trace import Tracer


class LLMError(Exception):
    """Raised when Gemini cannot produce an answer (no key, quota, bad reply)."""


def _looks_rate_limited(err: Exception) -> bool:
    text = f"{type(err).__name__} {err}".lower()
    return any(w in text for w in ("429", "quota", "rate", "resourceexhausted", "exhausted"))


class GeminiClient:
    """Lazily initialised so importing this module never needs the SDK."""

    def __init__(self) -> None:
        self._model = None
        self._calls = 0
        self._ready = False
        self._init_error: str | None = None

    # -- introspection --------------------------------------------------
    @property
    def available(self) -> bool:
        if not config.HAS_KEY:
            return False
        self._ensure_model()
        return self._ready

    @property
    def calls(self) -> int:
        """Number of real network calls made this session (for the UI badge)."""
        return self._calls

    # -- setup ----------------------------------------------------------
    def _ensure_model(self) -> None:
        if self._ready or self._init_error is not None:
            return
        try:
            import google.generativeai as genai  # imported lazily on purpose

            genai.configure(api_key=config.GEMINI_API_KEY)
            self._model = genai.GenerativeModel(config.GEMINI_MODEL)
            self._ready = True
        except Exception as err:  # SDK missing, bad key format, etc.
            self._init_error = str(err)
            self._ready = False

    # -- generation -----------------------------------------------------
    def generate(self, prompt: str, tracer: Tracer, json_mode: bool = False) -> str:
        """Return the model's text, retrying transient rate limits.

        Raises LLMError if the model is unavailable or every attempt fails.
        """
        if not self.available:
            raise LLMError(self._init_error or "Gemini is not configured")

        generation_config = {"temperature": 0.2}
        if json_mode:
            # Ask Gemini to answer with raw JSON so the router can parse it.
            generation_config["response_mime_type"] = "application/json"

        last_err: Exception | None = None
        for attempt in range(1, config.LLM_MAX_ATTEMPTS + 1):
            try:
                self._calls += 1
                start = time.perf_counter()
                resp = self._model.generate_content(  # type: ignore[union-attr]
                    prompt, generation_config=generation_config
                )
                ms = (time.perf_counter() - start) * 1000.0
                text = (getattr(resp, "text", "") or "").strip()
                if not text:
                    raise LLMError("Gemini returned an empty response")
                tracer.add(
                    "llm",
                    f"Gemini {config.GEMINI_MODEL}",
                    f"answered in {ms:.0f} ms",
                    ms=ms,
                )
                return text
            except LLMError:
                raise
            except Exception as err:
                last_err = err
                if _looks_rate_limited(err) and attempt < config.LLM_MAX_ATTEMPTS:
                    wait = config.LLM_BACKOFF_SECONDS * (2 ** (attempt - 1))
                    tracer.add(
                        "notice",
                        "Gemini rate limit (429)",
                        f"backing off {wait:.0f}s, retry {attempt}/{config.LLM_MAX_ATTEMPTS - 1}",
                    )
                    time.sleep(wait)
                    continue
                break

        raise LLMError(f"Gemini call failed: {last_err}")


def strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers if the model adds them anyway."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1] if "\n" in t else t.lstrip("`")
        if t.endswith("```"):
            t = t[: t.rfind("```")]
    return t.strip()
