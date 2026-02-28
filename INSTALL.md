# Installation & Setup Guide

Step-by-step instructions to install, configure, and run the **MCP Explained** project.

---

## Prerequisites

| Requirement | Minimum Version | Check |
|-------------|----------------|-------|
| Python | 3.11+ | `python3 --version` |
| pip | any | `pip3 --version` |
| Anthropic API key | — | [console.anthropic.com](https://console.anthropic.com/settings/keys) |

> **uv** (optional but recommended) — a fast Python package manager.
> If you don't have it, use pip instead (both methods are shown below).

---

## Step 1 — Get the Code

### Option A: Clone from GitHub
```bash
git clone https://github.com/shashipk/mcp_explained.git
cd mcp_explained
```

### Option B: Download ZIP
1. Go to the GitHub repo → click **Code** → **Download ZIP**
2. Unzip it, then open Terminal and `cd` into the folder:
   ```bash
   cd ~/Downloads/mcp_explained
   ```

### Option C: Already on your machine
```bash
cd ~/Desktop/Python\ Agents/Claude_Projects/mcp_explained
```

---

## Step 2 — Install Dependencies

Choose **one** of the following methods:

---

### Method A: uv (Recommended)

`uv` is a fast Rust-based Python package manager. If you already have Python 3.11+, install uv first:

```bash
# Install uv (one-time setup)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart your terminal, then verify:
uv --version
# Expected: uv 0.x.x
```

Then install the project dependencies:

```bash
# Inside the mcp_explained/ folder:
uv sync
```

What this does:
- Creates a `.venv/` virtual environment inside the project folder
- Installs all 4 dependencies: `mcp`, `anthropic`, `python-dotenv`, `rich`
- The `pyproject.toml` already has `package = false` set, so uv knows this
  is a scripts project and won't try to build/install it as a Python package

Expected output:
```
Using CPython 3.11.x
Creating virtual environment at: .venv
Resolved 41 packages in ...
Installed 38 packages in ...
 + anthropic==0.84.x
 + mcp==1.26.x
 + python-dotenv==1.x.x
 + rich==14.x.x
 ...
```

---

### Method B: pip (Standard)

```bash
# Inside the mcp_explained/ folder:

# Create a virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate        # macOS / Linux
# OR
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

Expected output:
```
Collecting mcp>=1.0.0
Collecting anthropic>=0.40.0
Collecting python-dotenv>=1.0.0
Collecting rich>=13.0.0
...
Successfully installed anthropic-0.84.x mcp-1.26.x ...
```

---

## Step 3 — Set Up Your API Key

The client uses Claude (Anthropic's AI), which needs an API key.

### Get an API Key
1. Go to [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
2. Click **Create Key**
3. Name it `mcp-learning` (or anything)
4. Copy the key — it starts with `sk-ant-...`

> **Billing note:** You must add credits to your Anthropic account before the API will work.
> Go to [console.anthropic.com/settings/billing](https://console.anthropic.com/settings/billing) and add at least $5.
> The examples use `claude-haiku-4-5-20251001` (cheapest model) — a full demo session costs less than $0.01.

### Add the Key to `.env`

```bash
# In the mcp_explained/ folder:
cp .env.example .env
```

Now open `.env` in any text editor and replace the placeholder:

```
# Before:
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# After:
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxx
```

Save the file. Never commit this file to Git (it's already in `.gitignore`).

---

## Step 4 — Verify Everything Works

Run these checks before running the main scripts:

```bash
# Check 1: All packages importable
uv run python -c "import mcp, anthropic, dotenv, rich; print('✓ All packages OK')"
# Expected: ✓ All packages OK

# Check 2: API key is loaded
uv run python -c "
import os
from dotenv import load_dotenv
load_dotenv('.env', override=True)
key = os.environ.get('ANTHROPIC_API_KEY', '')
print('✓ API key loaded' if key.startswith('sk-ant') else '✗ Key missing or wrong format')
"

# Check 3: MCP server starts (press Ctrl+C after 2 seconds)
uv run python server/mcp_server.py
# Expected: no errors, it just waits (that's correct — it expects MCP client input)
```

> **If using pip instead of uv:** replace `uv run python` with `python3`
> (after activating your venv with `source .venv/bin/activate`)

---

## Step 5 — Run the Examples

### Example 1: Without MCP (Traditional Approach)

This shows the old way of integrating tools with AI — everything hardcoded in one file.

```bash
uv run python examples/01_without_mcp.py
```

What you'll see:
```
Example 1: Without MCP (Traditional Approach)

Problems you should notice after running this:
  ❌ Tool schemas are hardcoded in this file
  ❌ Tool logic is also hardcoded in this file
  ...

[WITHOUT MCP] Question: What is sqrt(2025) + 10 raised to the power of 3?
──────────────────────────────────────────────────────────
  Claude calls tool: calculate({'expression': 'sqrt(2025)'})
  Result: Result: 45.0
  Claude calls tool: calculate({'expression': '10 ** 3'})
  Result: Result: 1000

Claude's answer:
The square root of 2025 is 45, and 10 raised to the power of 3 is 1000.
So, sqrt(2025) + 10³ = 45 + 1000 = 1045.
```

Try a custom question:
```bash
uv run python examples/01_without_mcp.py "What is 15 squared plus the square root of 144?"
```

---

### Example 2: With MCP (The MCP Way)

Same question, same answer — but now tools live in a separate reusable server.

```bash
uv run python examples/02_with_mcp.py
```

What you'll see:
```
Example 2: With MCP (The Right Way)

┌─────────────────────────────┬────────────────────────────────────────┐
│       WITHOUT MCP            │           WITH MCP                     │
├─────────────────────────────┼────────────────────────────────────────┤
│ Tool schemas: hardcoded here │ Tool schemas: from server              │
│ Tool logic: hardcoded here   │ Tool logic: runs in server             │
...

[WITH MCP] Question: What is sqrt(2025) + 10 raised to the power of 3?
──────────────────────────────────────────────────────────
  Discovered 7 tools from MCP server:
    • calculate
    • get_weather
    • save_note
    • get_note
    • list_notes
    • get_datetime
    • word_count

  Claude calls tool: calculate({'expression': 'sqrt(2025)'})
  Result: Expression: sqrt(2025) / Result: 45.0
  ...

Claude's answer:
sqrt(2025) + 10³ = 45 + 1000 = 1045.
```

Key thing to notice: this file has **zero** tool implementation code. It all comes from the server.

---

### Example 3: Interactive Client (Full Experience)

The most complete demo — ask Claude anything, it uses all 7 tools.

```bash
uv run python client/mcp_client.py
```

This opens an interactive prompt. Try these questions:

```
You: What is the surface area of a sphere with radius 7? Use 4 * pi * r^2

You: What's the weather in Mumbai, London, and Tokyo right now?

You: Save a note called 'what-is-mcp' with the text: MCP is a protocol that standardizes how AI models connect to tools and data sources.

You: Show me all my saved notes.

You: Read the note called 'what-is-mcp'

You: Count the words in: Model Context Protocol lets you build AI tools once and reuse them with any AI model.

You: What is today's date and time?
```

Press `Ctrl+C` to exit.

### Run a scripted demo (shows all 7 tools automatically):
```bash
uv run python client/mcp_client.py --demo
```

### Ask a single question and exit:
```bash
uv run python client/mcp_client.py "What is log base 2 of 1024?"
```

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set"
```
Error: ANTHROPIC_API_KEY not set. Run: cp .env.example .env
```

**Most likely cause:** Your shell already has `ANTHROPIC_API_KEY` set as an empty string,
and `load_dotenv` doesn't override existing shell variables by default.
All files in this project use `override=True` to handle this, but first check:

```bash
# 1. Make sure .env exists and has the key (not the placeholder)
cat .env | grep ANTHROPIC

# 2. Confirm it loads correctly
uv run python -c "
from dotenv import load_dotenv; import os
load_dotenv('.env', override=True)
key = os.environ.get('ANTHROPIC_API_KEY', '')
print('OK' if key.startswith('sk-ant') else 'Missing — check your .env file')
"
```

---

### "ModuleNotFoundError: No module named 'mcp'"
**Fix:** You're not using the project's virtual environment.

With uv: prefix every command with `uv run`:
```bash
uv run python client/mcp_client.py   # ✓ correct
python client/mcp_client.py          # ✗ uses system Python, not venv
```

With pip: activate the venv first:
```bash
source .venv/bin/activate            # macOS/Linux
python client/mcp_client.py         # now uses venv Python
```

---

### "uv sync" fails with build error
If you see a hatchling error like "Unable to determine which files to ship",
your uv may be older. Update uv and try again:
```bash
uv self update
uv sync
```

---

### Server seems to hang / no output
`server/mcp_server.py` is designed to run as a **subprocess** launched by the client — it waits for JSON-RPC input on stdin. Running it directly will show no output (that's normal). Always run the client, which launches the server automatically:
```bash
uv run python client/mcp_client.py   # ✓ launches server internally
uv run python server/mcp_server.py   # ✓ correct only for testing; press Ctrl+C to exit
```

---

### "credit balance is too low"
```
anthropic.BadRequestError: Your credit balance is too low to access the Anthropic API.
```
Add credits at [console.anthropic.com/settings/billing](https://console.anthropic.com/settings/billing). A $5 top-up is enough for hundreds of runs of this project.

---

### API rate limit error
If you see `RateLimitError`, wait 30 seconds and try again. The examples use `claude-haiku-4-5-20251001` (fastest + cheapest) to minimize this.

---

## File Reference

| File | Command to run |
|------|---------------|
| Examples side-by-side comparison | `uv run python examples/01_without_mcp.py` then `uv run python examples/02_with_mcp.py` |
| Interactive client | `uv run python client/mcp_client.py` |
| Scripted demo (all 7 tools) | `uv run python client/mcp_client.py --demo` |
| Single question | `uv run python client/mcp_client.py "your question here"` |
| MCP server (for inspection) | `uv run python server/mcp_server.py` then Ctrl+C |
