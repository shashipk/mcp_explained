#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                     MCP SERVER — The Tool Provider                  ║
║                                                                      ║
║  This is one half of the MCP architecture.                          ║
║                                                                      ║
║  WHAT IT DOES:                                                       ║
║    Exposes a set of "tools" (functions) over the MCP protocol so    ║
║    that any MCP-compatible AI client can discover and call them.    ║
║                                                                      ║
║  WHY IT'S SEPARATE FROM THE CLIENT:                                 ║
║    - A server can be reused across many AI apps (Claude, GPT, etc.) ║
║    - Tools are defined ONCE, not duplicated in every app            ║
║    - You can update tools without touching AI client code           ║
║    - Community can publish MCP servers (like npm packages for AI)   ║
║                                                                      ║
║  HOW IT COMMUNICATES:                                               ║
║    Uses "stdio" transport — the client launches this as a           ║
║    subprocess and they talk via stdin/stdout (JSON-RPC messages).   ║
║    Other transports exist: SSE (HTTP), WebSocket, etc.             ║
╚══════════════════════════════════════════════════════════════════════╝

Tools exposed by this server:
  1. calculate    — evaluate math expressions safely
  2. get_weather  — mock weather data for any city
  3. save_note    — persist a note to disk
  4. get_note     — retrieve a note by key
  5. list_notes   — list all saved note keys
  6. get_datetime — current date/time in any timezone
  7. word_count   — count words/chars in a piece of text
"""

import json
import math
import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ─────────────────────────────────────────────────────────────
# SERVER INIT
# ─────────────────────────────────────────────────────────────

# Every MCP server has a name. Clients see this when they connect.
app = Server("learning-mcp-server")

# Where notes are persisted (sibling "data/" folder)
NOTES_FILE = Path(__file__).parent.parent / "data" / "notes.json"


# ─────────────────────────────────────────────────────────────
# HELPERS — Notes persistence
# ─────────────────────────────────────────────────────────────

def _load_notes() -> dict:
    """Load notes from JSON file on disk."""
    if NOTES_FILE.exists():
        try:
            return json.loads(NOTES_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_notes(notes: dict) -> None:
    """Persist notes dict to JSON file."""
    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOTES_FILE.write_text(json.dumps(notes, indent=2))


# ─────────────────────────────────────────────────────────────
# MCP HANDLER: list_tools
#
# This is the "discovery" endpoint. When a client connects,
# it calls list_tools() to learn what this server can do.
# No hardcoding in the client — it just reads what's here.
# ─────────────────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    Advertise all available tools to connecting clients.

    MCP KEY CONCEPT:
      The client calls this once after connecting to discover
      what tools exist. This is "dynamic discovery" — the
      client doesn't need to know the tools ahead of time.
    """
    return [
        # ── Tool 1: Calculator ───────────────────────────────
        types.Tool(
            name="calculate",
            description=(
                "Safely evaluate a mathematical expression. "
                "Supports: +, -, *, /, //, %, ** (power), "
                "and all Python math functions: sqrt, sin, cos, "
                "tan, log, log2, log10, floor, ceil, pi, e, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": (
                            "Math expression to evaluate. "
                            "Examples: '2 + 2', 'sqrt(144)', "
                            "'pi * 5**2', 'log(1000, 10)'"
                        ),
                    }
                },
                "required": ["expression"],
            },
        ),

        # ── Tool 2: Weather ──────────────────────────────────
        types.Tool(
            name="get_weather",
            description=(
                "Get current weather information for any city. "
                "NOTE: This returns mock/simulated data for "
                "learning purposes — in a real project, this "
                "would call a live weather API (OpenWeatherMap, etc.)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. 'Mumbai', 'San Francisco', 'Berlin'",
                    }
                },
                "required": ["city"],
            },
        ),

        # ── Tool 3: Save Note ────────────────────────────────
        types.Tool(
            name="save_note",
            description=(
                "Save a text note to persistent storage. "
                "Notes survive between sessions. Use a descriptive "
                "key so you can retrieve the note later."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Unique identifier for the note, e.g. 'meeting-2026-02-28'",
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content to save",
                    },
                },
                "required": ["key", "content"],
            },
        ),

        # ── Tool 4: Get Note ─────────────────────────────────
        types.Tool(
            name="get_note",
            description="Retrieve a previously saved note by its key.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key of the note to retrieve",
                    }
                },
                "required": ["key"],
            },
        ),

        # ── Tool 5: List Notes ───────────────────────────────
        types.Tool(
            name="list_notes",
            description="List all saved note keys with their save timestamps.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),

        # ── Tool 6: Date/Time ────────────────────────────────
        types.Tool(
            name="get_datetime",
            description=(
                "Get the current date and time. "
                "Returns UTC time plus common timezone offsets."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": (
                            "Output format: 'full' (default) or 'date' or 'time'. "
                            "full=date+time+day, date=date only, time=time only"
                        ),
                        "enum": ["full", "date", "time"],
                        "default": "full",
                    }
                },
                "required": [],
            },
        ),

        # ── Tool 7: Word Count ───────────────────────────────
        types.Tool(
            name="word_count",
            description=(
                "Count words, characters, sentences, and paragraphs in text. "
                "Useful for checking essay lengths, tweet character limits, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to analyse",
                    }
                },
                "required": ["text"],
            },
        ),
    ]


# ─────────────────────────────────────────────────────────────
# MCP HANDLER: call_tool
#
# When Claude (or any AI client) decides to use a tool, it
# sends a call_tool request here. The server executes the
# logic and returns the result as TextContent.
#
# MCP KEY CONCEPT:
#   The AI never runs tool code itself. It sends a request,
#   the server executes it in a controlled environment, and
#   returns structured results. This is safe, auditable, and
#   lets you add logging/rate-limiting/auth in one place.
# ─────────────────────────────────────────────────────────────

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """
    Execute a tool and return its result.

    Parameters:
        name      – tool name (must match one declared in list_tools)
        arguments – dict matching the tool's inputSchema

    Returns:
        List of TextContent blocks (MCP supports mixed content:
        text, images, embedded resources — we use text here)
    """

    # ── Tool 1: Calculator ───────────────────────────────────
    if name == "calculate":
        expression = arguments.get("expression", "")

        # Build a safe evaluation context using Python's math module.
        # We explicitly allow only math functions — no builtins like
        # __import__, exec, open, etc. This prevents code injection.
        safe_context: dict[str, Any] = {
            k: getattr(math, k)
            for k in dir(math)
            if not k.startswith("_")
        }
        safe_context["abs"] = abs
        safe_context["round"] = round
        safe_context["min"] = min
        safe_context["max"] = max

        try:
            result = eval(expression, {"__builtins__": {}}, safe_context)  # noqa: S307
            return [types.TextContent(
                type="text",
                text=f"Expression: {expression}\nResult: {result}"
            )]
        except Exception as exc:
            return [types.TextContent(
                type="text",
                text=f"Error evaluating '{expression}': {exc}"
            )]

    # ── Tool 2: Weather (mock) ───────────────────────────────
    elif name == "get_weather":
        city = arguments.get("city", "Unknown")

        # Mock data — in production this would be a real API call.
        # MCP makes it easy to swap this out: update the server only,
        # no client changes needed.
        import hashlib
        seed = int(hashlib.md5(city.lower().encode()).hexdigest()[:8], 16)  # noqa: S324
        conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Windy", "Overcast"]
        condition = conditions[seed % len(conditions)]
        temp_c = 15 + (seed % 25)  # 15–40°C range, deterministic per city
        humidity = 30 + (seed % 60)

        weather = {
            "city": city,
            "condition": condition,
            "temperature_celsius": temp_c,
            "temperature_fahrenheit": round(temp_c * 9 / 5 + 32, 1),
            "humidity_percent": humidity,
            "wind_kmh": 5 + (seed % 40),
            "data_source": "mock — replace with real API for production",
        }
        return [types.TextContent(
            type="text",
            text=json.dumps(weather, indent=2)
        )]

    # ── Tool 3: Save Note ────────────────────────────────────
    elif name == "save_note":
        key = arguments.get("key", "").strip()
        content = arguments.get("content", "").strip()

        if not key:
            return [types.TextContent(type="text", text="Error: 'key' cannot be empty.")]
        if not content:
            return [types.TextContent(type="text", text="Error: 'content' cannot be empty.")]

        notes = _load_notes()
        notes[key] = {
            "content": content,
            "saved_at": datetime.utcnow().isoformat() + "Z",
            "word_count": len(content.split()),
        }
        _save_notes(notes)

        return [types.TextContent(
            type="text",
            text=f"✓ Note '{key}' saved successfully ({len(content.split())} words)."
        )]

    # ── Tool 4: Get Note ─────────────────────────────────────
    elif name == "get_note":
        key = arguments.get("key", "").strip()
        notes = _load_notes()

        if key not in notes:
            all_keys = list(notes.keys())
            hint = f"Available keys: {all_keys}" if all_keys else "No notes saved yet."
            return [types.TextContent(
                type="text",
                text=f"No note found with key '{key}'. {hint}"
            )]

        note = notes[key]
        return [types.TextContent(
            type="text",
            text=(
                f"Note: {key}\n"
                f"Saved at: {note['saved_at']}\n"
                f"─────────────────────\n"
                f"{note['content']}"
            )
        )]

    # ── Tool 5: List Notes ───────────────────────────────────
    elif name == "list_notes":
        notes = _load_notes()

        if not notes:
            return [types.TextContent(type="text", text="No notes saved yet.")]

        lines = ["Saved notes:"]
        for key, note in notes.items():
            lines.append(f"  • {key}  (saved {note['saved_at']}, {note.get('word_count', '?')} words)")

        return [types.TextContent(type="text", text="\n".join(lines))]

    # ── Tool 6: Date/Time ────────────────────────────────────
    elif name == "get_datetime":
        fmt = arguments.get("format", "full")
        now = datetime.now(timezone.utc)

        if fmt == "date":
            text = now.strftime("%Y-%m-%d (%A, %B %d, %Y)")
        elif fmt == "time":
            text = now.strftime("%H:%M:%S UTC")
        else:  # full
            text = (
                f"Date: {now.strftime('%A, %B %d, %Y')}\n"
                f"Time (UTC): {now.strftime('%H:%M:%S')}\n"
                f"ISO 8601:   {now.isoformat()}\n"
                f"Unix epoch: {int(now.timestamp())}"
            )

        return [types.TextContent(type="text", text=text)]

    # ── Tool 7: Word Count ───────────────────────────────────
    elif name == "word_count":
        text = arguments.get("text", "")

        words = len(text.split())
        chars_with_spaces = len(text)
        chars_no_spaces = len(text.replace(" ", ""))
        sentences = len(re.split(r"[.!?]+", text.strip())) if text.strip() else 0
        paragraphs = len([p for p in text.split("\n\n") if p.strip()])

        result = {
            "words": words,
            "characters_with_spaces": chars_with_spaces,
            "characters_without_spaces": chars_no_spaces,
            "sentences": max(sentences - 1, 0),
            "paragraphs": max(paragraphs, 1 if text.strip() else 0),
            "avg_word_length": round(chars_no_spaces / words, 1) if words else 0,
        }
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    else:
        return [types.TextContent(
            type="text",
            text=f"Unknown tool: '{name}'. Check list_tools() for available tools."
        )]


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
#
# When launched as a subprocess by an MCP client, this starts
# the stdio transport loop. The server reads JSON-RPC messages
# from stdin and writes responses to stdout — all handled by
# the MCP library automatically.
# ─────────────────────────────────────────────────────────────

async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
