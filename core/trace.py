"""A tiny execution tracer.

Instead of streaming logs over Server-Sent Events, Lumen collects the story of
a single request into a list of steps and returns the whole timeline with the
answer. The browser then renders it as a "How I got this" panel.
"""
from __future__ import annotations

import time
from typing import Dict, List


class Tracer:
    """Accumulates ordered steps, each with an optional duration in ms."""

    def __init__(self) -> None:
        self._steps: List[Dict[str, object]] = []

    def add(self, kind: str, title: str, detail: str = "", ms: float | None = None) -> None:
        self._steps.append(
            {
                "n": len(self._steps) + 1,
                "kind": kind,          # router | http | llm | cache | fallback | notice
                "title": title,
                "detail": detail,
                "ms": None if ms is None else round(ms, 1),
            }
        )

    def timed(self, kind: str, title: str):
        """Context manager that records how long a block took.

        Usage:
            with tracer.timed("http", "GET weather"):
                ...
        The recorded step's detail can be filled in afterwards via .last().
        """
        return _Timed(self, kind, title)

    def last(self) -> Dict[str, object]:
        return self._steps[-1]

    def as_list(self) -> List[Dict[str, object]]:
        return list(self._steps)


class _Timed:
    def __init__(self, tracer: Tracer, kind: str, title: str) -> None:
        self._tracer = tracer
        self._kind = kind
        self._title = title
        self._start = 0.0

    def __enter__(self) -> Tracer:
        self._start = time.perf_counter()
        return self._tracer

    def __exit__(self, exc_type, exc, tb) -> bool:
        elapsed = (time.perf_counter() - self._start) * 1000.0
        # Attach timing to the most recent step the block created, if any,
        # otherwise create a bare timed step.
        if self._tracer.as_list():
            self._tracer.last()["ms"] = round(elapsed, 1)
        else:
            self._tracer.add(self._kind, self._title, ms=elapsed)
        return False  # never swallow exceptions
