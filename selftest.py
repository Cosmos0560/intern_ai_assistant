"""Offline self-test for Lumen — no API key and no Gemini calls required.

It checks the two parts that must work on their own:
  1. the keyword router picks the right source for a range of questions, and
  2. each connector fetches live data and the offline templates render an answer.

Run:
    python selftest.py
"""
from __future__ import annotations

import sys

from core.engine import Engine
from core.router import keyword_route

ROUTER_CASES = [
    ("What is the weather in Paris?", "weather"),
    ("temperature in Tashkent", "weather"),
    ("Show me information about GitHub.", "github"),
    ("tell me about the torvalds/linux repo", "github"),
    ("price of bitcoin", "crypto"),
    ("how much is ethereum worth", "crypto"),
    ("what is the meaning of life", "none"),
]

LIVE_CASES = [
    "What is the weather in Paris?",
    "Show me information about GitHub.",
    "price of bitcoin",
]


def main() -> int:
    failures = 0

    print("Router (offline keyword rules)")
    for question, expected in ROUTER_CASES:
        got = keyword_route(question)["source"]
        ok = got == expected
        failures += 0 if ok else 1
        print(f"  {'PASS' if ok else 'FAIL'}  {question!r:45} -> {got} (want {expected})")

    print("\nLive pipeline (real APIs, offline templates)")
    engine = Engine()
    for question in LIVE_CASES:
        try:
            res = engine.ask(question)
            answer = res["answer"]
            ok = bool(answer) and res["source"] != "none"
            failures += 0 if ok else 1
            print(f"  {'PASS' if ok else 'FAIL'}  [{res['source']}] {answer[:88]}")
        except Exception as err:  # network hiccup, etc.
            failures += 1
            print(f"  FAIL  {question!r} raised {type(err).__name__}: {err}")

    print("\n" + ("ALL TESTS PASSED" if failures == 0 else f"{failures} TEST(S) FAILED"))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
