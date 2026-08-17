│   ├── prompt.get
│   └── memory.read
├── Policy engine
├── Memory layer
├── Local model layer
└── Tests + CI + diagnostics
```

## Installation

Create the virtual environment and install the canonical developer dependency set:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` is the single developer entrypoint and includes the runtime and test requirement files. The runtime requirements use Python's Android platform marker to skip desktop-only native dependencies such as ChromaDB and `uvicorn[standard]` on Termux. This means the canonical command is safe on Android as well as desktop Python.

For a minimal mobile/Termux runtime environment, use:

```bash
pip install -r requirements-runtime-mobile.txt
```

The mobile file remains the leanest option and deliberately uses the built-in SQLite memory adapter.

## Local runtime

Default local services:

- Ollama: `http://127.0.0.1:11434`
- Memory API: `http://127.0.0.1:5000`
- Default model: `llama3.2:3b`

Start the runtime:

```bash
runtime/project-nas.sh start
```

Check it:

```bash
runtime/project-nas.sh status
runtime/project-nas.sh doctor
```
