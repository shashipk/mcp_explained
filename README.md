# MCP Explained — Understanding Model Context Protocol Through Code

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-1.0+-purple?logo=anthropic&logoColor=white)](https://modelcontextprotocol.io)
[![Claude](https://img.shields.io/badge/Claude-claude--opus--4--6-orange?logo=anthropic)](https://anthropic.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> A hands-on learning project that explains **MCP (Model Context Protocol)** through working Python code — what it is, why it exists, and how it makes AI tool integrations simpler and more powerful.

---

## Table of Contents

- [What is MCP?](#what-is-mcp)
- [Why Do We Need MCP?](#why-do-we-need-mcp)
- [How MCP Works](#how-mcp-works)
- [This Project](#this-project)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Suggested Learning Path](#suggested-learning-path)
- [Running the Examples](#running-the-examples)
- [Key Concepts Deep Dive](#key-concepts-deep-dive)
- [MCP Ecosystem](#mcp-ecosystem)
- [Troubleshooting](#troubleshooting)
- [Full Installation Guide →](INSTALL.md)

---

## What is MCP?

**Model Context Protocol (MCP)** is an open standard developed by Anthropic (and now adopted broadly) that defines a **standardized way for AI models to connect to external tools, data sources, and services**.

Think of it like **USB for AI tools**:
- USB standardized how devices connect to computers — one port, infinite compatible devices
- MCP standardizes how tools connect to AI models — one protocol, infinite compatible tools and AI models

Before MCP, every developer had to build custom integrations between their tools and each AI model. After MCP, you build your tool server once and it works with any MCP-compatible AI.

### In Simple Terms

```
Without MCP: "I need to write code to make my tool work with Claude,
              then rewrite it for GPT, then again for Gemini..."

With MCP:    "I build an MCP server once. Claude, GPT, Gemini — they
              all connect to the same server using the same protocol."
```

---

## Why Do We Need MCP?

### The Problem: N × M Integrations

Imagine you have **5 tools** (calculator, database, file system, weather API, calendar) and **4 AI models** (Claude, GPT-4, Gemini, Llama). Without a standard:

```
5 tools × 4 AI models = 20 custom integrations to build and maintain
```

Every integration has its own schema format, calling convention, response format, auth mechanism, and error handling — all different, all duplicated.

### The Solution: N + M Integrations

With MCP:

```
5 tools (each as an MCP server)  +  4 AI clients (each MCP-compatible)
= 9 total things to build
```

Each tool is written **once** as an MCP server. Each AI client is built **once** as an MCP client. They all talk to each other through the standard protocol.

### Additional Problems MCP Solves

| Problem | Without MCP | With MCP |
|---------|------------|----------|
| **Tool reuse** | Copy-paste code between apps | Point any app to the same server |
| **Discoverability** | Hardcode which tools exist | Client discovers tools at runtime |
| **Separation of concerns** | Tool code mixed with AI logic | Clean split: server = tools, client = AI |
| **Ecosystem** | Each developer reinvents the wheel | Growing library of reusable servers |
| **Updates** | Update tool = update every AI app | Update server = all clients get it |
| **Security** | Tool code runs anywhere | Tool code runs in a controlled server |

---

## How MCP Works

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         YOUR APPLICATION                         │
│                                                                  │
│  ┌──────────────────┐            ┌─────────────────────────┐    │
│  │    MCP CLIENT     │           │      Claude API          │    │
│  │  (mcp_client.py) │◄─────────►│  (or GPT / Gemini / ...) │   │
│  └────────┬─────────┘            └─────────────────────────┘    │
│           │                                                      │
│     MCP Protocol                                                 │
│     (JSON-RPC over stdio / SSE / WebSocket)                     │
│           │                                                      │
│  ┌────────▼─────────┐                                           │
│  │    MCP SERVER     │                                           │
│  │  (mcp_server.py) │                                           │
│  │                  │                                           │
│  │  Tools exposed:  │                                           │
│  │   • calculate    │                                           │
│  │   • get_weather  │                                           │
│  │   • save_note    │                                           │
│  │   • get_note     │                                           │
│  │   • list_notes   │                                           │
│  │   • get_datetime │                                           │
│  │   • word_count   │                                           │
│  └──────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Communication Flow (Step by Step)

```
User types: "What is sqrt(144) + 10^2?"
                    │
                    ▼
           MCP Client sends to Claude API
           (includes list of tools discovered from MCP server)
                    │
                    ▼
         Claude thinks: "I need the calculator tool"
         Claude responds: tool_use { name: "calculate", input: {...} }
                    │
                    ▼
         MCP Client routes to MCP Server via call_tool()
         Server executes the calculation
         Server returns: "Result: 112"
                    │
                    ▼
         MCP Client sends tool_result back to Claude
                    │
                    ▼
         Claude responds: "sqrt(144) is 12, and 10² is 100, so the answer is 112."
                    │
                    ▼
         User sees the final answer
```

### The Protocol: JSON-RPC over stdio

MCP uses **JSON-RPC 2.0** — a simple request/response format. This is what actually flows between client and server:

```json
// Client → Server: "What tools do you have?"
{ "jsonrpc": "2.0", "method": "tools/list", "id": 1 }

// Server → Client: "Here are my tools"
{ "jsonrpc": "2.0", "result": { "tools": [...] }, "id": 1 }

// Client → Server: "Run the calculator"
{ "jsonrpc": "2.0", "method": "tools/call",
  "params": { "name": "calculate", "arguments": { "expression": "sqrt(144)" } },
  "id": 2 }

// Server → Client: "Here's the result"
{ "jsonrpc": "2.0", "result": { "content": [{ "type": "text", "text": "Result: 12" }] }, "id": 2 }
```

All of this happens automatically — the `mcp` Python library handles it. You just write the tool logic and the library does the messaging.

---

## This Project

### Tools Built in the MCP Server

| Tool | What it does | What it demonstrates |
|------|-------------|----------------------|
| `calculate` | Evaluate math expressions safely | Tools can wrap existing Python libraries |
| `get_weather` | Return mock weather for any city | Tools can call external APIs |
| `save_note` | Persist a note to `data/notes.json` | Tools can read/write files (stateful) |
| `get_note` | Retrieve a note by key | Tools can return stored data |
| `list_notes` | List all saved note keys | Tools can have no required parameters |
| `get_datetime` | Return current UTC date/time | Simple utility tools |
| `word_count` | Count words/chars/sentences in text | Text processing tools |

### Files and Their Purpose

| File | Purpose |
|------|---------|
| `server/mcp_server.py` | The MCP server — defines and runs all 7 tools |
| `client/mcp_client.py` | The MCP client — connects to server, uses Claude to answer questions |
| `examples/01_without_mcp.py` | Traditional approach — tools hardcoded in the AI client |
| `examples/02_with_mcp.py` | MCP approach — same result, zero tool code in the client |

---

## Project Structure

```
mcp_explained/
│
├── README.md                    ← You are here
├── pyproject.toml               ← Project dependencies (uv)
├── requirements.txt             ← Same deps for pip users
├── .env.example                 ← API key template
├── .gitignore
│
├── server/
│   └── mcp_server.py            ← THE MCP SERVER
│                                   Exposes 7 tools via stdio transport
│                                   Any MCP-compatible AI can connect to this
│
├── client/
│   └── mcp_client.py            ← THE MCP CLIENT
│                                   Connects to server, uses Claude + MCP
│                                   Interactive CLI + scripted demo mode
│
├── examples/
│   ├── 01_without_mcp.py        ← Traditional approach (hardcoded tools)
│   └── 02_with_mcp.py           ← MCP approach (dynamic discovery)
│
└── data/
    └── notes.json               ← Persisted notes (created at runtime)
```

---

## Quick Start

> 📖 **Need more detail?** See the [full step-by-step installation guide](INSTALL.md) which covers both uv and pip methods, verification steps, all run commands, and a complete troubleshooting section.

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- An Anthropic API key with billing enabled ([get one here](https://console.anthropic.com/settings/keys))

> **Billing note:** This project uses `claude-haiku-4-5-20251001` for examples (cheapest model).
> A full demo session costs less than **$0.01**. Add at minimum $5 credit at
> [console.anthropic.com/settings/billing](https://console.anthropic.com/settings/billing).

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/shashipk/mcp_explained.git
cd mcp_explained
```

---

### Step 2 — Install dependencies

**With uv (recommended):**
```bash
uv sync
```

**With pip:**
```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
pip install -r requirements.txt
```

---

### Step 3 — Add your API key

```bash
cp .env.example .env
```

Open `.env` in any editor and replace the placeholder:
```
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
```

> **How to get the key:**
> 1. Go to [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
> 2. Click **Create Key**, name it anything (e.g. `mcp-learning`)
> 3. Copy the key — it starts with `sk-ant-...`
> 4. Paste it into `.env` (no quotes around the value)

---

### Step 4 — Verify everything works

```bash
# Check that all packages are importable
uv run python -c "import mcp, anthropic, dotenv, rich; print('All OK')"
# Expected: All OK

# Confirm your API key loads
uv run python -c "
from dotenv import load_dotenv; import os
load_dotenv('.env', override=True)
key = os.environ.get('ANTHROPIC_API_KEY', '')
print('Key OK' if key.startswith('sk-ant') else 'Key missing — check your .env')
"
```

---

## Suggested Learning Path

If you're new to MCP, go in this order:

```
1. Read "What is MCP?" and "Why Do We Need MCP?" above
         ↓
2. Run Example 1 (without MCP) — see the problem
   uv run python examples/01_without_mcp.py
         ↓
3. Run Example 2 (with MCP) — see the solution
   uv run python examples/02_with_mcp.py
         ↓
4. Compare the two files side by side in your editor
   Open: examples/01_without_mcp.py  vs  examples/02_with_mcp.py
         ↓
5. Read the server code with comments
   Open: server/mcp_server.py
         ↓
6. Read the client code with comments
   Open: client/mcp_client.py
         ↓
7. Run the interactive client and experiment
   uv run python client/mcp_client.py
```

---

## Running the Examples

> **Note for pip users:** If you used pip instead of uv, activate your venv first:
> `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows)
> Then use `python` instead of `uv run python`.

---

### Example 1: Without MCP (The Old Way)

```bash
uv run python examples/01_without_mcp.py
```

**What to notice in the output:**
- Tool schemas are defined in the file (search for `TOOLS_HARDCODED_IN_THIS_FILE`)
- Tool logic runs in the file (see `execute_tool_locally()`)
- To add a new tool, you'd have to modify this file

**Try a custom question:**
```bash
uv run python examples/01_without_mcp.py "What is 15 squared plus sqrt(81)?"
```

---

### Example 2: With MCP (The Right Way)

```bash
uv run python examples/02_with_mcp.py
```

**What to notice:**
- Zero tool schemas in this file — `session.list_tools()` gets them from the server
- Zero tool logic in this file — `session.call_tool()` runs it in the server
- This file would automatically gain any new tool you add to `server/mcp_server.py`

**Try the same custom question:**
```bash
uv run python examples/02_with_mcp.py "What is 15 squared plus sqrt(81)?"
```

Same answer. Completely different architecture.

---

### Interactive Client (Full Experience)

```bash
# Interactive mode — ask Claude anything
uv run python client/mcp_client.py

# Pass a question directly
uv run python client/mcp_client.py "What is the area of a circle with radius 5?"

# Scripted demo — automatically shows all 7 tools
uv run python client/mcp_client.py --demo
```

**Questions to try covering all 7 tools:**

```
# Calculator
"What is log base 2 of 1024, and what is 15 factorial?"

# Weather
"Compare the weather in Tokyo, Mumbai, and New York."

# Notes — try these in sequence
"Save a note called 'mcp-insight' with this text: MCP lets you build tools once and reuse them with any AI."
"What notes do I have saved?"
"Read the note called 'mcp-insight'"

# Word count
"How many words are in: Four score and seven years ago our fathers brought forth on this continent a new nation."

# Date / Time
"What day of the week is it today, and what is the Unix timestamp right now?"
```

---

## Key Concepts Deep Dive

### 1. MCP Server (`server/mcp_server.py`)

An MCP server is a Python script with two handlers:

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

app = Server("my-server")

# Handler 1: Tell clients what tools exist
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="my_tool",
            description="Does something useful",  # Claude reads this to decide when to use the tool
            inputSchema={"type": "object", "properties": {...}}
        )
    ]

# Handler 2: Execute a tool when called
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "my_tool":
        result = do_something(arguments)
        return [types.TextContent(type="text", text=result)]
```

### 2. MCP Client (`client/mcp_client.py`)

An MCP client connects to the server and bridges it with the AI:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 1. Define how to launch the server
server_params = StdioServerParameters(command="python", args=["server/mcp_server.py"])

# 2. Connect
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()                    # MCP handshake

        tools = await session.list_tools()            # discover tools dynamically
        result = await session.call_tool(name, args)  # execute a tool in the server
```

### 3. Transport Layers

MCP supports multiple ways for the client and server to communicate:

| Transport | Use Case | How it works |
|-----------|----------|--------------|
| **stdio** | Local tools (same machine) | Client launches server as subprocess; communicate via stdin/stdout |
| **SSE (HTTP)** | Remote tools (different machine) | Server runs as HTTP endpoint; client connects via Server-Sent Events |
| **WebSocket** | Bidirectional remote tools | Full-duplex connection |

This project uses **stdio** — the simplest to set up and run locally. In production, you'd use SSE or WebSocket to expose the server over a network so multiple clients can connect.

### 4. Tool Schema (JSON Schema)

Each tool is described with a JSON Schema. Claude uses this to understand what parameters to send:

```python
types.Tool(
    name="calculate",
    description="Evaluate a math expression",   # ← Claude reads this to decide WHEN to use the tool
    inputSchema={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "e.g. 'sqrt(144)', '2 + 2 * 10'"  # ← Claude reads this to format its call
            }
        },
        "required": ["expression"]
    }
)
```

### 5. The Agentic Loop

Claude doesn't call all tools upfront — it reasons one step at a time:

```
Turn 1  →  User: "What is sqrt(144)?"
Turn 2  →  Claude: tool_use { name: "calculate", input: { "expression": "sqrt(144)" } }
Turn 3  →  User:   tool_result { content: "Result: 12.0" }
Turn 4  →  Claude: "The square root of 144 is 12."   [stop_reason: "end_turn"]
```

For complex questions, Claude may call multiple tools across multiple turns before giving its final answer.

### 6. MCP vs Native Tool Use

You might wonder: "Claude already supports tool use natively — why add MCP on top?"

| Aspect | Native Tool Use (no MCP) | With MCP |
|--------|--------------------------|----------|
| Tool schemas | Hardcoded in your app | Defined in a reusable server |
| Tool logic | Runs in your app | Runs in the server |
| Reusability | Zero — per-app copy-paste | Full — any MCP client connects |
| Multi-model | Must rewrite per model | One server works for all |
| Discovery | Static — you define it up front | Dynamic — client asks server at runtime |
| Ecosystem | None — you build everything | Hundreds of community servers available |

MCP is a **standardization layer** on top of native tool use. The client still sends native Anthropic-format tool calls — MCP just defines how the tools are discovered and executed in a separate server.

---

## Understanding the Code Side by Side

The same question, two architectures:

**Without MCP** (`examples/01_without_mcp.py`):
```python
# ❌ Tool schemas defined HERE (in the AI client)
TOOLS = [{"name": "calculate", "description": "...", "input_schema": {...}}]

# ❌ Tool logic runs HERE (in the AI client)
def execute_tool_locally(name, args):
    if name == "calculate":
        return str(eval(args["expression"], ...))

# ❌ Reuse = copy-paste this entire file into every new app
```

**With MCP** (`examples/02_with_mcp.py`):
```python
# ✅ Tool schemas come FROM the server (zero hardcoding here)
tools_response = await session.list_tools()
anthropic_tools = [{"name": t.name, ...} for t in tools_response.tools]

# ✅ Tool logic runs IN the server (zero implementation code here)
result = await session.call_tool(block.name, block.input)

# ✅ Reuse = point any new app at the same server
```

---

## MCP Ecosystem

MCP has been adopted by all major AI platforms:

- **Anthropic** — Claude Desktop, Claude API
- **OpenAI** — ChatGPT (MCP support announced 2025)
- **Google** — Gemini (community MCP clients)
- **Microsoft** — GitHub Copilot, VS Code AI extensions

### Community MCP Servers

The community has already built hundreds of ready-to-use MCP servers:

| Server | What it connects to |
|--------|---------------------|
| `mcp-server-filesystem` | Local file system (read/write files) |
| `mcp-server-git` | Git repositories |
| `mcp-server-github` | GitHub API (issues, PRs, repos) |
| `mcp-server-postgres` | PostgreSQL databases |
| `mcp-server-brave-search` | Brave web search |
| `mcp-server-puppeteer` | Browser automation |
| `mcp-server-slack` | Slack messaging |

Find more at: [github.com/modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)

---

## Troubleshooting

### API key not loading (`ANTHROPIC_API_KEY not set`)

If you see this error even after setting the key in `.env`, your shell may already have `ANTHROPIC_API_KEY` set as an empty string — `load_dotenv` doesn't override existing shell variables by default.

All files in this project already include `override=True` to handle this:
```python
load_dotenv(Path(__file__).parent.parent / ".env", override=True)
```

If you're still having issues, verify:
```bash
# Does the .env file exist and contain the key?
cat .env | grep ANTHROPIC_API_KEY

# Does it load correctly?
uv run python -c "
from dotenv import load_dotenv; import os
load_dotenv('.env', override=True)
key = os.environ.get('ANTHROPIC_API_KEY', '')
print('OK' if key.startswith('sk-ant') else 'Missing or wrong format')
"
```

---

### `credit balance is too low`

```
anthropic.BadRequestError: Your credit balance is too low to access the Anthropic API.
```

Add credits at [console.anthropic.com/settings/billing](https://console.anthropic.com/settings/billing). A $5 top-up is enough for hundreds of runs of this project.

---

### `ModuleNotFoundError: No module named 'mcp'`

You're running Python outside the virtual environment. Use `uv run python` instead of `python`:

```bash
uv run python examples/01_without_mcp.py    # ✓ uses venv
python examples/01_without_mcp.py           # ✗ uses system Python
```

Or with pip, activate the venv first:
```bash
source .venv/bin/activate
python examples/01_without_mcp.py
```

---

### Server seems to hang with no output

`server/mcp_server.py` is designed to be **launched as a subprocess by the client** — it waits for JSON-RPC input on stdin. Running it directly shows no output (that's correct — it's waiting for a client). Always run the client instead:

```bash
uv run python client/mcp_client.py    # ✓ the client launches the server automatically
```

---

## License

MIT — see [LICENSE](LICENSE)

---

## Author

Built as a learning project to understand MCP through working code. If this helped you, give it a ⭐ on GitHub!

---

*Uses `claude-opus-4-6` for the interactive client and `claude-haiku-4-5-20251001` for examples (faster and cheaper for demos).*
