// Lumen front-end: one POST per question, then render answer + trace timeline.
(function () {
  "use strict";

  const form = document.getElementById("askForm");
  const input = document.getElementById("q");
  const askBtn = document.getElementById("ask");
  const loading = document.getElementById("loading");
  const result = document.getElementById("result");

  const answerEl = document.getElementById("answer");
  const sourceTag = document.getElementById("sourceTag");
  const modeTag = document.getElementById("modeTag");
  const cacheTag = document.getElementById("cacheTag");
  const traceEl = document.getElementById("trace");
  const rawEl = document.getElementById("raw");
  const callBadge = document.getElementById("callBadge");

  const SOURCE_LABEL = {
    weather: "weather",
    github: "github",
    crypto: "crypto",
    none: "no match",
  };

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      input.value = chip.textContent.trim();
      form.requestSubmit();
    });
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;

    setBusy(true);
    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      render(await res.json());
    } catch (err) {
      renderError(err);
    } finally {
      setBusy(false);
    }
  });

  function setBusy(busy) {
    askBtn.disabled = busy;
    loading.classList.toggle("hidden", !busy);
    if (busy) result.classList.add("hidden");
  }

  function render(data) {
    answerEl.textContent = data.answer || "";

    sourceTag.textContent = SOURCE_LABEL[data.source] || data.source || "—";
    modeTag.textContent = data.mode === "ai" ? "Gemini answer" : "offline answer";
    modeTag.classList.toggle("is-offline", data.mode !== "ai");
    cacheTag.classList.toggle("hidden", !data.cached);

    // timeline
    traceEl.innerHTML = "";
    (data.trace || []).forEach((step) => {
      const li = document.createElement("li");
      li.className = "k-" + step.kind;
      const ms = step.ms != null ? `<span class="ti-ms">${step.ms} ms</span>` : "";
      const detail = step.detail ? `<div class="ti-detail">${escapeHtml(step.detail)}</div>` : "";
      li.innerHTML = `<div class="ti-title">${escapeHtml(step.title)}${ms}</div>${detail}`;
      traceEl.appendChild(li);
    });

    rawEl.textContent = data.raw ? JSON.stringify(data.raw, null, 2) : "(no raw data for this answer)";

    if (typeof data.gemini_calls === "number") {
      callBadge.textContent = data.gemini_calls + " calls";
    }
    result.classList.remove("hidden");
  }

  function renderError(err) {
    answerEl.textContent = "Something went wrong: " + err.message + ". Please try again.";
    sourceTag.textContent = "error";
    modeTag.textContent = "—";
    modeTag.classList.add("is-offline");
    cacheTag.classList.add("hidden");
    traceEl.innerHTML = "";
    rawEl.textContent = "";
    result.classList.remove("hidden");
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }
})();
