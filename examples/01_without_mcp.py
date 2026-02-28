#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║              EXAMPLE 1: WITHOUT MCP — The Traditional Way            ║
║                                                                      ║
║  Goal: Give Claude a calculator tool and ask it a math question.    ║
║                                                                      ║
║  This is how developers integrated tools with LLMs BEFORE MCP:     ║
║    - Tool schemas are hardcoded in this file                        ║
║    - Tool logic (execution code) is also hardcoded here             ║
║    - Everything is tightly coupled in one place                     ║
║                                                                      ║
║  PROBLEMS WITH THIS APPROACH:                                        ║
║                                                                      ║
║  ❌  Problem 1 — No Reusability                                      ║
║       If you build another AI app, you copy-paste the tool code.   ║
║       Bug in the tool? Fix it in every app. Updates are painful.   ║
║                                                                      ║
║  ❌  Problem 2 — Tight Coupling                                      ║
║       Tool definitions live inside the AI client code.             ║
║       They're not discoverable or shareable.                        ║
║                                                                      ║
║  ❌  Problem 3 — No Standardization                                  ║
║       OpenAI's tool format ≠ Anthropic's format ≠ Google's format.  ║
║       Build a tool for Claude? Rebuild it for GPT. Rebuild again   ║
║       for Gemini. N tools × M models = N×M custom integrations.    ║
║                                                                      ║
║  ❌  Problem 4 — Hard to Extend                                      ║
║       Adding a new tool means modifying this file and redeploying   ║
║       the entire AI application.                                    ║
║                                                                      ║
║  Run this: python examples/01_without_mcp.py                        ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import math
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# ─────────────────────────────────────────────────────────────
# ❌ HARDCODED TOOL SCHEMAS
#
# Every developer who wants a calculator tool must write this
# from scratch — or copy it from someone else's code.
# If Anthropic changes the schema format, you update every app.
# ─────────────────────────────────────────────────────────────
TOOLS_HARDCODED_IN_THIS_FILE = [
    {
        "name": "calculate",
        "description": "Evaluate a math expression. Supports +, -, *, /, **, sqrt, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression to evaluate",
                }
            },
            "required": ["expression"],
        },
    },
    {
        "name": "get_weather",
        "description": "Get weather for a city (mock data).",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name",
                }
            },
            "required": ["city"],
        },
    },
]


# ─────────────────────────────────────────────────────────────
# ❌ HARDCODED TOOL LOGIC
#
# The actual execution code is also here, mixed with AI logic.
# Tool code + AI orchestration code = one big tangled file.
# ─────────────────────────────────────────────────────────────
def execute_tool_locally(name: str, arguments: dict) -> str:
    """
    Tool logic hardcoded right here in the AI client.

    Compare this with the MCP approach where the client just calls:
        result = await session.call_tool(name, arguments)
    ...and the server handles ALL tool execution.
    """
    if name == "calculate":
        expression = arguments.get("expression", "")
        safe_ctx = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
        safe_ctx.update({"abs": abs, "round": round})
        try:
            result = eval(expression, {"__builtins__": {}}, safe_ctx)  # noqa: S307
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {e}"

    elif name == "get_weather":
        # Duplicate logic — also exists in server/mcp_server.py
        # Without MCP, there's no single source of truth.
        import hashlib
        city = arguments.get("city", "")
        seed = int(hashlib.md5(city.lower().encode()).hexdigest()[:8], 16)  # noqa: S324
        conditions = ["Sunny", "Cloudy", "Rainy", "Windy"]
        return f"{city}: {conditions[seed % len(conditions)]}, {15 + seed % 25}°C (mock)"

    return f"Unknown tool: {name}"


# ─────────────────────────────────────────────────────────────
# Ask Claude with hardcoded tools
# ─────────────────────────────────────────────────────────────
def ask_claude_without_mcp(question: str) -> str:
    """
    Standard Anthropic tool-use flow — no MCP involved.

    Notice: to add a new tool, you must:
      1. Add its schema to TOOLS_HARDCODED_IN_THIS_FILE
      2. Add its logic to execute_tool_locally()
      3. Redeploy this application

    With MCP, you'd only update the server. The client auto-discovers.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set. Copy .env.example → .env")
        sys.exit(1)

    client = Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": question}]

    print(f"\n[WITHOUT MCP] Question: {question}")
    print("─" * 60)

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            tools=TOOLS_HARDCODED_IN_THIS_FILE,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text

        elif response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  Claude calls tool: {block.name}({block.input})")

                    # ❌ Tool executes HERE in the client process
                    result = execute_tool_locally(block.name, block.input)
                    print(f"  Result: {result}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})

    return ""


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Example 1: Without MCP (Traditional Approach)")
    print("=" * 60)
    print()
    print("Problems you should notice after running this:")
    print("  ❌ Tool schemas are hardcoded in this file")
    print("  ❌ Tool logic is also hardcoded in this file")
    print("  ❌ To add a tool, you modify this file and redeploy")
    print("  ❌ These tools cannot be shared with another AI app")
    print()

    question = (
        sys.argv[1] if len(sys.argv) > 1
        else "What is sqrt(2025) + 10 raised to the power of 3? Also, what's the weather in Paris?"
    )

    answer = ask_claude_without_mcp(question)
    print(f"\nClaude's answer:\n{answer}")

    print()
    print("─" * 60)
    print("Next: Run examples/02_with_mcp.py to see the MCP way.")
    print("Same result, but tools live in a separate reusable server.")
