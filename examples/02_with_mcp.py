#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                 EXAMPLE 2: WITH MCP — The MCP Way                    ║
║                                                                      ║
║  Goal: Same as Example 1 — give Claude tools and ask a question.   ║
║                                                                      ║
║  Now we use MCP. Compare with examples/01_without_mcp.py           ║
║                                                                      ║
║  BENEFITS OF MCP VISIBLE IN THIS FILE:                              ║
║                                                                      ║
║  ✅  Benefit 1 — Zero Hardcoded Tool Schemas                         ║
║       We call session.list_tools() and get them from the server.   ║
║       No schema JSON in this file at all.                           ║
║                                                                      ║
║  ✅  Benefit 2 — Zero Hardcoded Tool Logic                           ║
║       We call session.call_tool() and the server executes it.       ║
║       No calculator/weather code in this file.                      ║
║                                                                      ║
║  ✅  Benefit 3 — Dynamic Discovery                                    ║
║       Add a new tool to server/mcp_server.py?                       ║
║       This client automatically sees and can use it — no changes!   ║
║                                                                      ║
║  ✅  Benefit 4 — Reusable Server                                     ║
║       The same server/mcp_server.py can serve Claude, GPT, Gemini, ║
║       or any other MCP-compatible AI. Write once, use everywhere.   ║
║                                                                      ║
║  ✅  Benefit 5 — Separation of Concerns                              ║
║       AI orchestration logic is here.                               ║
║       Tool implementation logic is in the server.                  ║
║       Clean, maintainable, independently updatable.                ║
║                                                                      ║
║  Run this: python examples/02_with_mcp.py                           ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

SERVER_SCRIPT = Path(__file__).parent.parent / "server" / "mcp_server.py"


# ─────────────────────────────────────────────────────────────
# Notice what is NOT in this file:
#   - No tool schemas                 (server provides them)
#   - No math.sqrt or eval()         (server handles it)
#   - No weather logic               (server handles it)
#   - No notes I/O code              (server handles it)
#
# This file only cares about: talking to Claude and routing
# tool calls to the MCP server. Clean separation!
# ─────────────────────────────────────────────────────────────

async def ask_claude_with_mcp(question: str) -> str:
    """
    Ask Claude a question with access to tools via MCP.

    STEP-BY-STEP MCP FLOW:
      1. Launch MCP server as subprocess (stdio_client)
      2. Open MCP session (ClientSession)
      3. Initialize the session (handshake)
      4. Discover tools from server (list_tools)
      5. Pass tools to Claude (no schemas hardcoded here!)
      6. Claude may call tools → route to server (call_tool)
      7. Return final answer
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set. Copy .env.example → .env")
        sys.exit(1)

    claude = Anthropic(api_key=api_key)

    print(f"\n[WITH MCP] Question: {question}")
    print("─" * 60)

    # ── Step 1 & 2: Start server + open communication ────────
    # StdioServerParameters tells MCP: "launch this script as a subprocess
    # and communicate with it via stdin/stdout"
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # ── Step 3: MCP Handshake ─────────────────────────
            # Sends {"jsonrpc":"2.0","method":"initialize",...}
            # Server responds with name, version, capabilities.
            await session.initialize()

            # ── Step 4: Discover tools ────────────────────────
            # ✅ NO HARDCODING — we ask the server what it has.
            # If someone added a new tool to the server yesterday,
            # we automatically get it here today.
            tools_response = await session.list_tools()

            print(f"  Discovered {len(tools_response.tools)} tools from MCP server:")
            for t in tools_response.tools:
                print(f"    • {t.name}")
            print()

            # Convert MCP format → Anthropic API format
            # (MCP uses the same JSON Schema standard, minimal conversion)
            anthropic_tools = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema,
                }
                for t in tools_response.tools
            ]

            # ── Step 5–6: Agentic loop ────────────────────────
            messages = [{"role": "user", "content": question}]

            while True:
                response = claude.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=512,
                    tools=anthropic_tools,
                    messages=messages,
                )

                # Claude finished reasoning
                if response.stop_reason == "end_turn":
                    for block in response.content:
                        if hasattr(block, "text"):
                            return block.text
                    return ""

                # Claude wants to use a tool
                if response.stop_reason == "tool_use":
                    messages.append({"role": "assistant", "content": response.content})

                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            print(f"  Claude calls tool: {block.name}({block.input})")

                            # ✅ Tool executes IN THE SERVER (not here!)
                            # This one line replaces all the tool logic that
                            # was in examples/01_without_mcp.py
                            result = await session.call_tool(block.name, block.input)

                            result_text = (
                                result.content[0].text
                                if result.content
                                else "No result"
                            )
                            print(f"  Result: {result_text[:100]}")

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_text,
                            })

                    messages.append({"role": "user", "content": tool_results})

    return ""


# ─────────────────────────────────────────────────────────────
# Side-by-side comparison helper
# ─────────────────────────────────────────────────────────────

def print_comparison() -> None:
    comparison = """
┌─────────────────────────────┬──────────────────────────────────────┐
│       WITHOUT MCP            │           WITH MCP                   │
├─────────────────────────────┼──────────────────────────────────────┤
│ Tool schemas: hardcoded here │ Tool schemas: from server            │
│ Tool logic: hardcoded here   │ Tool logic: runs in server           │
│ Add tool: modify this file   │ Add tool: modify server only         │
│ Reuse: copy-paste code       │ Reuse: point any app to this server  │
│ Multi-AI: rewrite per model  │ Multi-AI: one server works for all   │
│ Discovery: manual/static     │ Discovery: dynamic at runtime        │
└─────────────────────────────┴──────────────────────────────────────┘
"""
    print(comparison)


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Example 2: With MCP (The Right Way)")
    print("=" * 60)

    print_comparison()

    question = (
        sys.argv[1] if len(sys.argv) > 1
        else "What is sqrt(2025) + 10 raised to the power of 3? Also, what's the weather in Paris?"
    )

    answer = asyncio.run(ask_claude_with_mcp(question))
    print(f"\nClaude's answer:\n{answer}")

    print()
    print("─" * 60)
    print("Key takeaway: This file has ZERO tool implementation code.")
    print("All tool logic lives in server/mcp_server.py.")
    print("That server can serve ANY MCP-compatible AI client.")
