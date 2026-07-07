# xmas-bench
Aiming to create a credible, tested version of nytbench.

## Scraping NYT Mini crosswords

`scraper.py` downloads the most recent `NUM_CROSSWORDS` (from `config.py`) NYT Mini
crosswords and saves each as a `.puz` file in `puzzles/`. A NYT Crossword subscription is
required.

### Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in credentials
```

### Credentials

Edit `.env` and provide **either**:

- `NYT_S` — your NYT-S session cookie (preferred, most reliable), or
- `NYT_USERNAME` / `NYT_PASSWORD` — used only if `NYT_S` is empty. NYT's login is
  bot-protected and may fail, in which case use the cookie method below.

`.env` is gitignored, so your credentials stay out of the repo.

### How to get your NYT-S cookie

1. Log in at [nytimes.com](https://www.nytimes.com).
2. Open your browser's DevTools (`F12` or right-click → Inspect).
3. Go to **Application** (Chrome) or **Storage** (Firefox) → **Cookies** →
   `https://www.nytimes.com`.
4. Find the cookie named **`NYT-S`** and copy its value into `NYT_S=` in `.env`.

### Run

```bash
python src/scraper.py            # scrapes config.NUM_CROSSWORDS minis
python src/scraper.py --num 3    # scrape just the 3 most recent (handy for testing)
```

Output lands in `puzzles/` as `mini-YYYY-MM-DD.puz`. If a puzzle ever isn't
`.puz`-compatible, its raw JSON is saved as `mini-YYYY-MM-DD.json` instead.

## Open-source LLMs (`llm.py`)

`llm.py` is the zero-cost invocation layer for the multi-agent system. It calls
**open-source** models on free hosted tiers — OpenRouter and Groq — through the
OpenAI-compatible `openai` SDK. Models to test live in `config.MODELS`.

### Get free API keys (no credit card)

- **OpenRouter** — https://openrouter.ai/keys → set `OPENROUTER_API_KEY` in `.env`.
  Unlocks the best big open models (DeepSeek R1, Llama 3.3 70B, Qwen3 235B) via `:free` IDs.
- **Groq** — https://console.groq.com/keys → set `GROQ_API_KEY` in `.env`. Very fast;
  open-weight models like `openai/gpt-oss-120b` and `moonshotai/kimi-k2`.

At least one key is required.

### Use

```bash
python src/llm.py                                                    # smoke test -> prints "pong"
PYTHONPATH=src python -c "import llm; print(llm.list_models('groq'))"    # list live model IDs for a provider
```

```python
import llm
llm.chat([{"role": "user", "content": "Hi"}], model="deepseek-r1")   # one-shot -> str

solver = llm.Agent("solver", "You solve crossword clues.", model="llama-3.3-70b")
print(solver.send("5-letter fruit"))                                 # stateful agent
```

Free tiers are rate-limited (~20 req/min); the SDK auto-retries transient limits. Model IDs
drift — use `list_models(...)` to refresh the keys in `config.MODELS`.

## XMAS solver + replays

The Xword Multi-Agent System (XMAS) solves a puzzle by having LLM agents **propose** words/
letters while a deterministic grid manager **applies** only what fits the crossings. Variants
(which agents + which procedure steps) live in `config.XMAS_VARIANTS`.

Benchmark a variant across puzzles (resumable; results cached under `results/<variant>/`):

```bash
python src/benchmark.py --variant baseline --num 5
```

Generate a turn-by-turn **replay** of a single solve as a self-contained HTML file:

```bash
python src/replay.py --variant baseline --puzzle mini-2026-07-05   # --puzzle defaults to newest
```

Open `replays/<variant>/<puzzle>.html` in a browser: step/play through the grid filling in,
with an event log of every agent proposal (candidates shown), placement, and cell guess, plus a
"show correctness" toggle. The replay re-runs the solve with tracing, so its score may differ
slightly from a cached benchmark run (model nondeterminism).
