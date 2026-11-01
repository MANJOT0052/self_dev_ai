"""Autonomous, test-gated self-development loop.

The agent asks a local Ollama coding model for an improvement, applies it in the
working tree, runs the project's test command, and keeps the change only when
checks pass. Every accepted iteration is committed to Git. It never pushes to
GitHub by itself; pushing remains an explicit user action.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from urllib import request

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "update_code.py"
STATE = ROOT / ".self_dev_state.json"
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

SYSTEM_PROMPT = """You are an autonomous but safety-focused software engineer.
Improve the supplied project code. Return ONLY a complete replacement for the
requested target file, with no markdown fences. Preserve the public behavior
unless an improvement is clearly needed. Do not add malware, credential theft,
secrets, destructive shell commands, hidden persistence, or arbitrary network
access. Keep changes small, readable and testable. Do not modify files outside
the repository. The replacement must be valid Python.
"""


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def ask_ollama(source: str, model: str, test_output: str = "") -> str:
    prompt = (
        f"{SYSTEM_PROMPT}\n\nTarget: {TARGET.name}\nCurrent source:\n{source}\n"
        f"\nPrevious test output (if any):\n{test_output[-6000:]}\n"
        "Return only the replacement source."
    )
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = request.Request(
        "http://localhost:11434/api/generate", data=payload,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with request.urlopen(req, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8")).get("response", "").strip()
    if not result:
        raise RuntimeError("Ollama returned an empty response")
    if result.startswith("```"):
        result = result.replace("```python", "", 1).replace("```", "").strip()
    return result + "\n"


def test_command() -> list[str]:
    configured = os.getenv("SELF_DEV_TEST")
    if configured:
        return configured.split()
    return [os.environ.get("PYTHON", "python"), "-m", "pytest", "-q"]


def git_clean() -> bool:
    return not run(["git", "status", "--porcelain"]).stdout.strip()


def commit(message: str) -> None:
    run_result = run(["git", "add", TARGET.name])
    if run_result.returncode:
        raise RuntimeError(run_result.stderr)
    run_result = run(["git", "commit", "-m", message])
    if run_result.returncode:
        raise RuntimeError(run_result.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test-gated autonomous self-development")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.iterations < 1 or args.iterations > 20:
        raise SystemExit("--iterations must be between 1 and 20")
    if not git_clean():
        raise SystemExit("Working tree is not clean. Commit or stash your changes first.")

    old = TARGET.read_text(encoding="utf-8")
    last_test = ""
    accepted = 0
    for i in range(args.iterations):
        print(f"[self-dev] iteration {i + 1}/{args.iterations}")
        candidate = ask_ollama(old, args.model, last_test)
        if candidate == old:
            print("[self-dev] model proposed no change; stopping.")
            break
        if args.dry_run:
            print(candidate)
            break

        TARGET.write_text(candidate, encoding="utf-8")
        test = run(test_command())
        last_test = (test.stdout + "\n" + test.stderr).strip()
        if test.returncode != 0:
            TARGET.write_text(old, encoding="utf-8")
            print("[self-dev] tests failed; candidate reverted.")
            print(last_test[-4000:])
            break

        commit(f"self-dev: iteration {i + 1} passes tests")
        old = candidate
        accepted += 1
        print("[self-dev] accepted and committed.")

    STATE.write_text(json.dumps({"accepted_iterations": accepted}, indent=2) + "\n", encoding="utf-8")
    print(f"[self-dev] done; accepted {accepted} iteration(s).")


if __name__ == "__main__":
    main()
