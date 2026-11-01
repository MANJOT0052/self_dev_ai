"""Safe self-development loop for self_dev_ai.

The agent can inspect its own source and ask a local Ollama model for a proposed
patch, but it never writes changes automatically. Proposed changes are saved as
patch files for human review first.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
from pathlib import Path
from urllib import request

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "update_code.py"
PROPOSALS = ROOT / "proposals"

SYSTEM_PROMPT = """You are a careful software engineer. Improve the supplied Python file.
Return ONLY the complete replacement source code, no markdown fences.
Do not add malware, credential theft, destructive commands, hidden network access,
or code that modifies files outside the project. Keep the program simple and testable.
"""


def read_target() -> str:
    return TARGET.read_text(encoding="utf-8")


def ask_ollama(source: str, model: str) -> str:
    prompt = f"{SYSTEM_PROMPT}\n\nCurrent file:\n{source}\n\nImprove reliability, clarity and maintainability."
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
    result = data.get("response", "").strip()
    if not result:
        raise RuntimeError("Ollama returned an empty response")
    return result


def make_diff(old: str, new: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=str(TARGET),
            tofile=str(TARGET) + " (proposal)",
        )
    )


def save_proposal(old: str, new: str) -> Path:
    PROPOSALS.mkdir(exist_ok=True)
    index = len(list(PROPOSALS.glob("proposal_*.py"))) + 1
    source_path = PROPOSALS / f"proposal_{index:03d}.py"
    diff_path = PROPOSALS / f"proposal_{index:03d}.diff"
    source_path.write_text(new + "\n", encoding="utf-8")
    diff_path.write_text(make_diff(old, new), encoding="utf-8")
    return source_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a reviewed self-improvement proposal.")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"))
    args = parser.parse_args()

    old = read_target()
    print(f"Analyzing {TARGET.name} with {args.model} ...")
    new = ask_ollama(old, args.model)
    proposal = save_proposal(old, new)
    print(f"Proposal created: {proposal}")
    print("No production file was changed. Review the .diff before applying it.")


if __name__ == "__main__":
    main()
