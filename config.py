NUM_CROSSWORDS = 100
OUTPUT_DIR = "puzzles"

# Open-source LLMs to test behind the multi-agent system.
# key -> (provider, model_id). Edit freely; use llm.list_models(provider) to see live IDs.
MODELS = {
    # OpenRouter free tier (needs OPENROUTER_API_KEY). Verified live Jul 2026.
    "nemotron-super": ("openrouter", "nvidia/nemotron-3-super-120b-a12b:free"),
    "hermes-405b":    ("openrouter", "nousresearch/hermes-3-llama-3.1-405b:free"),
    "qwen3-80b":      ("openrouter", "qwen/qwen3-next-80b-a3b-instruct:free"),
    "gpt-oss-120b":   ("openrouter", "openai/gpt-oss-120b:free"),
    "llama-3.3-70b":  ("openrouter", "meta-llama/llama-3.3-70b-instruct:free"),
    # Groq free tier (needs GROQ_API_KEY).
    "kimi-k2":        ("groq", "moonshotai/kimi-k2-instruct-0905"),
    # Local Ollama (no key) — for free XMAS development.
    "qwen2.5-7b":     ("ollama", "qwen2.5:7b"),
}
DEFAULT_MODEL = "nemotron-super"
TEMPERATURE = 0.2
MAX_TOKENS = 1024
REQUEST_TIMEOUT = 60

# Multi-agent crossword solver.
TOP_K = 5                       # candidate words the proposer returns per clue
MAX_ROUNDS = 4                  # propose/place rounds before giving up
PROPOSER_MODEL = "qwen2.5-7b"   # per-agent models -> lets us compare models
CELL_MODEL = "qwen2.5-7b"
RESULTS_DIR = "results"

# XMAS (Xword Multi-Agent System) variants: compose roles + procedure.
# Add/remove/reorder to make a new system.
XMAS_VARIANTS = {
    "baseline": {
        "roles": {"proposer": PROPOSER_MODEL, "cell": CELL_MODEL},
        "pipeline": ["propose_words", "apply_greedy", "cell_cascade"],
        "rounds": MAX_ROUNDS,
    },
    "words_only": {   # example: drop the cell role + cascade step
        "roles": {"proposer": PROPOSER_MODEL},
        "pipeline": ["propose_words", "apply_greedy"],
        "rounds": MAX_ROUNDS,
    },
}
DEFAULT_VARIANT = "baseline"