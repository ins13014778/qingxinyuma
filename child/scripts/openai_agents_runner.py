"""OpenAI Agents SDK — Simple Runner for qingxinyuma Electron IDE.

Thin wrapper that delegates to the unified turn runner in 'simple' mode.
Preserves backward compatibility with --prompt-file / --config-file CLI interface
while gaining Prompt API, ModelSettings, and Responses API support.

For the full-featured runner with tools, handoffs, guardrails, hooks, and streaming,
use openai_agents_turn_runner.py directly with --mode turn.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path


def load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_config(path: str) -> dict:
    raw = load_text(path).strip()
    if not raw:
        return {}
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OpenAI Agents simple runner (delegates to unified runner)"
    )
    parser.add_argument("--prompt-file", required=True, help="Path to text file with user prompt")
    parser.add_argument("--config-file", required=True, help="Path to JSON file with model config")
    args = parser.parse_args()

    # Ensure the turn runner's directory is on the import path
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    from openai_agents_turn_runner import run_simple

    prompt = load_text(args.prompt_file)
    config = load_config(args.config_file)

    request = {
        "prompt": prompt,
        "modelConfig": config,
    }

    try:
        final_output = asyncio.run(run_simple(request))
        if final_output:
            print(final_output)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
