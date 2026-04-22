import argparse
import json
import os
import sys
from pathlib import Path

from openai import AsyncOpenAI
from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled


SYSTEM_PROMPT = (
    "You are a pragmatic software engineering assistant. "
    "Follow the user prompt exactly, respond in plain text, and keep the answer concise."
)


def load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_config(path: str) -> dict:
    raw = load_text(path).strip()
    if not raw:
        return {}
    return json.loads(raw)


def normalize_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None

    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        normalized = normalized[: -len("/chat/completions")]
    return normalized


def resolve_model_config(config: dict) -> tuple[str, str | None, str]:
    api_key = (config.get("apiKey") or "").strip() or (config.get("api_key") or "").strip()
    base_url = (config.get("baseUrl") or "").strip() or (config.get("base_url") or "").strip()
    model = (config.get("model") or "").strip()

    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not base_url:
        base_url = os.environ.get("OPENAI_BASE_URL", "").strip()
    if not model:
        model = os.environ.get("OPENAI_MODEL", "").strip()

    if not api_key:
        raise RuntimeError("Missing API key. Configure a custom model or set OPENAI_API_KEY.")
    if not model:
        raise RuntimeError("Missing model name. Select a custom model or set OPENAI_MODEL.")

    return api_key, normalize_base_url(base_url), model


def format_output(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--config-file", required=True)
    args = parser.parse_args()

    prompt = load_text(args.prompt_file)
    config = load_config(args.config_file)
    api_key, base_url, model_name = resolve_model_config(config)

    set_tracing_disabled(True)

    client = AsyncOpenAI(api_key=api_key, base_url=base_url or None)
    model = OpenAIChatCompletionsModel(model=model_name, openai_client=client)
    agent = Agent(
        name="AilyOpenAIAgents",
        instructions=SYSTEM_PROMPT,
        model=model,
    )

    try:
        result = Runner.run_sync(agent, prompt)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    output = format_output(result.final_output)
    if output:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
