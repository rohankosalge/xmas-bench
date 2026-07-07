"""Free, open-source LLM tooling for the multi-agent system.

Talks to OpenRouter and Groq (both OpenAI-compatible) via the openai SDK.
Set OPENROUTER_API_KEY and/or GROQ_API_KEY in .env (see README).

    python llm.py                     # smoke test the default model
    llm.chat(messages, model=...)     # one-shot completion -> str
    llm.Agent(name, system_prompt)    # stateful chat agent for multi-agent use
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

import config

load_dotenv()

# provider -> (base_url, api-key env var). key_env None = local, no auth (Ollama).
PROVIDERS = {
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "ollama": ("http://localhost:11434/v1", None),
}

_clients = {}


def _client(provider):
    if provider not in _clients:
        base_url, key_env = PROVIDERS[provider]
        key = "ollama" if key_env is None else os.getenv(key_env)
        if not key:
            raise RuntimeError(f"Missing {key_env} in .env (see README).")
        _clients[provider] = OpenAI(
            base_url=base_url, api_key=key,
            timeout=config.REQUEST_TIMEOUT, max_retries=3,
        )
    return _clients[provider]


def chat(messages, model=config.DEFAULT_MODEL, **overrides):
    """Run a chat completion and return the reply text."""
    provider, model_id = config.MODELS[model]
    resp = _client(provider).chat.completions.create(
        model=model_id,
        messages=messages,
        temperature=overrides.get("temperature", config.TEMPERATURE),
        max_tokens=overrides.get("max_tokens", config.MAX_TOKENS),
    )
    return resp.choices[0].message.content


def list_models(provider):
    """Live model IDs offered by a provider (handy since free IDs drift)."""
    return [m.id for m in _client(provider).models.list().data]


def next_token_logprobs(messages, model):
    """First-token candidates as [(token, logprob)], or None if unsupported."""
    provider, model_id = config.MODELS[model]
    try:
        resp = _client(provider).chat.completions.create(
            model=model_id, messages=messages, max_tokens=1,
            temperature=0, logprobs=True, top_logprobs=20,
        )
        return [(t.token, t.logprob) for t in resp.choices[0].logprobs.content[0].top_logprobs]
    except Exception:
        return None


class Agent:
    """A named, stateful chat agent. Give each agent its own model to compare them."""

    def __init__(self, name, system_prompt, model=config.DEFAULT_MODEL):
        self.name = name
        self.model = model
        self.history = [{"role": "system", "content": system_prompt}]

    def send(self, message):
        self.history.append({"role": "user", "content": message})
        reply = chat(self.history, model=self.model)
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self):
        self.history = self.history[:1]


if __name__ == "__main__":
    print(chat([{"role": "user", "content": "Reply with exactly: pong"}]))
