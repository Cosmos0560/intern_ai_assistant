
from __future__ import annotations
"""Lumen — a natural-language data assistant (Flask entry point).

Ask a question in plain English. Lumen picks a public API, fetches live data,
and Google Gemini writes a short answer from exactly what was fetched.

Run:
    python app.py
Then open http://127.0.0.1:5000
"""

import os
import requests
from flask import Flask, jsonify, render_template, request

print(os.getenv("GITHUB_TOKEN"))

headers = {"Authorization": f"token {os.getenv('GITHUB_TOKEN')}"}
resp = requests.get("https://api.github.com/users/github", headers=headers)


from core import Engine
from core import config

app = Flask(__name__)
engine = Engine()


@app.get("/")
def home():
    return render_template("index.html", status=engine.status())


@app.get("/api/health")
def health():
    return jsonify(engine.status())


@app.post("/api/query")
def query():
    body = request.get_json(silent=True) or {}
    question = body.get("question", "")
    result = engine.ask(question)
    return jsonify(result)


def main() -> None:
    banner = [
        "  Lumen is running",
        f"  Open   : http://{config.HOST}:{config.PORT}",
        f"  Model  : {config.GEMINI_MODEL}",
        "  Gemini : key detected (live answers)"
        if config.HAS_KEY
        else "  Gemini : no key — offline fallback (still fetches real data)",
    ]
    width = max(len(line) for line in banner) + 2
    print("┌" + "─" * width + "┐")
    for line in banner:
        print("│ " + line.ljust(width - 1) + "│")
    print("└" + "─" * width + "┘")
    app.run(host=config.HOST, port=config.PORT, debug=False)


if __name__ == "__main__":
    main()
