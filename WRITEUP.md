# Homework 1 — Simple AI Data Assistant (write-up)

**By Otabek Yakubov**

## What I built

I built a small web app called **Lumen**. You type a question in normal English,
and it answers you using real data pulled live from the internet. It handles the
two example questions from the task — "What is the weather in Paris?" and
"Show me information about GitHub." — and I also added cryptocurrency prices, so
you can ask things like "price of bitcoin".

## Which tool (AI) I used

I used **Google Gemini** through its official Python library
(`google-generativeai`), with a free-tier "flash-lite" model. I read the model
name and API key from a `.env` file so nothing is hard-coded. The free tier
needs no credit card — you just get a key from Google AI Studio.

The assistant uses the model **twice** per question: once to read the question
and decide which data source fits, and once to turn the raw data I fetched into
a short, friendly answer.

## Which APIs / data sources I used

I picked free public APIs on purpose so the project costs nothing to run and
needs no keys for the data itself:

- **Weather** — `wttr.in`, which returns current conditions as JSON for a city
  name (temperature, feels-like, humidity, wind, description).
- **GitHub** — the official GitHub REST API, for a user/organisation or a
  specific `owner/repo`.
- **Crypto** — CoinGecko, which gives the current price, market cap, and 24-hour
  change for a coin.

## How the assistant works, step by step

1. The user types a question (or clicks an example button).
2. The browser sends the question to my Flask server as a single request.
3. **Step 1 (routing):** the server asks Gemini to answer with strict JSON such
   as `{"source":"weather","params":{"city":"Paris"}}`, and parses it safely.
4. **Step 2 (fetch real data):** based on that JSON, the server calls the correct
   public API and gets back real data.
5. **Step 3 (AI answer):** the server sends that raw data back to Gemini and asks
   it to write a short answer using only the data, so it does not invent facts.
6. The page shows the final answer, a **"How I got this"** timeline of every step
   (routing decision, the real HTTP call with its status code and timing), and
   the raw JSON that was fetched.

## Things I added so it is safe to demo

Because each question uses two Gemini calls and the free tier has limits, I added
a few safeguards: it retries with exponential backoff if Gemini replies "429 too
many requests", it caches answers for 10 minutes so repeating a question does not
use quota, and the header shows how many Gemini calls I have made. Most
importantly, if there is no key or a call fails, the app switches to local logic
(keyword routing + a template answer) and **still fetches the real data** — so
the whole pipeline works end to end even with no key at all.

## What the screenshots show (for submission)

1. The question typed into the box (with the example chips).
2. The **"How I got this"** timeline: the chosen source and the real
   `GET → HTTP 200` call to the public API, with its timing — this is the
   workflow / API-call evidence the task asks for.
3. The raw JSON panel expanded, next to the answer — proof the AI summarised the
   data that was actually fetched.
4. The final answer card with the source badge and the Gemini-calls counter.
