# self_dev_ai

A small self-development experiment: an AI can inspect `update_code.py` and generate an improvement proposal with a local Ollama model.

## Safety

The agent **does not automatically overwrite its own production code**. It writes proposed source and a unified diff under `proposals/` so the changes can be reviewed first.

## Run

1. Install and start Ollama.
2. Make sure your chosen coding model is available (default: `qwen2.5-coder:7b`).
3. Run:

```bash
python self_dev_ai.py
```

To use another model:

```bash
python self_dev_ai.py --model your-model-name
```

The current project intentionally remains tiny: `update_code.py` is the file being improved, while `self_dev_ai.py` is the proposal engine.
