#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                    MCP CLIENT — The AI Consumer                      ║
║                                                                      ║
║  This is the other half of the MCP architecture.                    ║
║                                                                      ║
║  WHAT IT DOES:                                                       ║
║    1. Launches the MCP server as a subprocess                       ║
║    2. Discovers available tools dynamically (no hardcoding!)        ║
║    3. Sends user questions to Claude                                 ║
║    4. When Claude wants a tool, routes the call to the MCP server   ║
║    5. Returns the result to Claude so it can answer the user        ║
║                                                                      ║
║  THE KEY INSIGHT:                                                    ║
║    This client doesn't know ANYTHING about the tools upfront.       ║
║    It just asks the server "what can you do?" and passes that       ║
║    info to Claude. Claude figures out which tools to call.          ║
║                                                                      ║
║  FLOW DIAGRAM:                                                       ║
║                                                                      ║
║    User question                                                     ║
║         │                                                            ║
║         ▼                                                            ║
║    [Claude API] ──────────── tool_use ──────────► [MCP Server]     ║
║         │                                              │            ║
║         │◄──────────────── tool_result ───────────────┘            ║
║         │                                                            ║
║         ▼                                                            ║
║    Final answer to user                                              ║
╚══════════════════════════════════════════════════════════════════════╝

Run this file directly:
    python client/mcp_client.py

Or with a specific question:
    python client/mcp_client.py "What is the square root of 256?"
"""

import asyncio
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

# ─────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────

# Load .env (ANTHROPIC_API_KEY)
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

console = Console()

# The MCP server script path
SERVER_SCRIPT = Path(__file__).parent.parent / "server" / "mcp_server.py"

# Model to use for answering
MODEL = "claude-opus-4-6"


# ─────────────────────────────────────────────────────────────
# Core MCP Client function
# ─────────────────────────────────────────────────────────────

async def ask_with_mcp(question: str, verbose: bool = True) -> str:
    """
    Ask Claude a question. Claude can use any tool the MCP server provides.

    MCP CLIENT LIFECYCLE:
      1. StdioServerParameters — tells the client HOW to launch the server
         (command + args). The client starts it as a subprocess.

      2. stdio_client(server_params) — opens stdin/stdout communication
         channels with the server subprocess.

      3. ClientSession — handles the MCP handshake (initialize request/
         response) and provides typed methods like list_tools, call_tool.

      4. session.initialize() — sends the MCP "initialize" request so the
         server knows a client has connected and negotiates capabilities.

      5. session.list_tools() — calls list_tools() on the server to get
         the tool definitions. These are then passed to Claude.

      6. Agentic loop — Claude may decide to use 0, 1, or many tools.
         We keep looping until Claude's stop_reason is "end_turn".
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not set. Run: cp .env.example .env[/red]")
        sys.exit(1)

    claude = Anthropic(api_key=api_key)

    # ── Step 1: Define HOW to launch the MCP server ──────────
    # The client will run: python server/mcp_server.py
    # And communicate with it via stdin/stdout (stdio transport).
    server_params = StdioServerParameters(
        command=sys.executable,          # use the same Python interpreter
        args=[str(SERVER_SCRIPT)],
    )

    # ── Step 2: Connect to the MCP server ────────────────────
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:

            # ── Step 3: Initialize the MCP session ───────────
            # This sends {"method": "initialize", ...} to the server.
            # The server responds with its name, version, and capabilities.
            await session.initialize()

            # ── Step 4: Discover tools dynamically ───────────
            # We ask the server: "What tools do you have?"
            # No hardcoding — tools are discovered at runtime!
            tools_response = await session.list_tools()

            # Convert MCP tool format → Anthropic API format
            # MCP and Anthropic both use JSON Schema for tool definitions,
            # so this conversion is straightforward.
            anthropic_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
                for tool in tools_response.tools
            ]

            if verbose:
                # Show what tools were discovered
                table = Table(title="Tools discovered from MCP server", show_lines=True)
                table.add_column("Tool", style="cyan", no_wrap=True)
                table.add_column("Description")
                for t in anthropic_tools:
                    table.add_row(t["name"], t["description"][:80] + "...")
                console.print(table)
                console.print()

            # ── Step 5: Agentic loop ──────────────────────────
            # Claude may call 0, 1, or many tools before giving
            # its final answer. We keep sending messages until
            # Claude signals it's done (stop_reason == "end_turn").
            messages = [{"role": "user", "content": question}]
            final_answer = ""

            while True:
                if verbose:
                    console.print("[dim]→ Calling Claude API...[/dim]")

                response = claude.messages.create(
                    model=MODEL,
                    max_tokens=1024,
                    tools=anthropic_tools,
                    messages=messages,
                )

                # ── Case A: Claude is done ────────────────────
                if response.stop_reason == "end_turn":
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_answer = block.text
                    break

                # ── Case B: Claude wants to use a tool ────────
                if response.stop_reason == "tool_use":
                    # Add Claude's response (with tool_use blocks) to history
                    messages.append({"role": "assistant", "content": response.content})

                    # Execute each tool call via the MCP session
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            if verbose:
                                console.print(
                                    f"  [yellow]⚡ Claude calls:[/yellow] "
                                    f"[cyan]{block.name}[/cyan]({block.input})"
                                )

                            # ── THE MAGIC OF MCP ──────────────────────────
                            # session.call_tool() sends a JSON-RPC message
                            # to the server subprocess and waits for the result.
                            # The server runs the actual logic; the client just
                            # forwards results back to Claude.
                            result = await session.call_tool(block.name, block.input)

                            result_text = (
                                result.content[0].text
                                if result.content
                                else "No result returned"
                            )

                            if verbose:
                                console.print(f"  [green]✓ Result:[/green] {result_text[:120]}")

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_text,
                            })

                    # Feed tool results back to Claude for its next response
                    messages.append({"role": "user", "content": tool_results})

    return final_answer


# ─────────────────────────────────────────────────────────────
# Interactive CLI
# ─────────────────────────────────────────────────────────────

SAMPLE_QUESTIONS = [
    "What is the square root of 2025 multiplied by pi?",
    "What's the weather like in Mumbai and New York today?",
    "Save a note called 'mcp-insight' with this text: MCP separates tools from AI clients. Tools are defined once and reused across any AI app.",
    "Retrieve the note I just saved called 'mcp-insight'.",
    "How many words are in this sentence: The Model Context Protocol standardizes how AI models connect to external tools and data sources.",
    "What is today's date and time?",
]


async def interactive_mode() -> None:
    """Run an interactive Q&A session with the MCP-powered Claude."""
    console.print(Panel.fit(
        "[bold cyan]MCP Explained — Interactive Client[/bold cyan]\n"
        "[dim]Claude answers your questions using tools from the MCP server.[/dim]",
        border_style="cyan",
    ))

    console.print("\n[bold]Sample questions you can try:[/bold]")
    for i, q in enumerate(SAMPLE_QUESTIONS, 1):
        console.print(f"  {i}. {q}")

    console.print("\n[dim]Type a question, or press Ctrl+C to exit.[/dim]\n")

    while True:
        try:
            question = console.input("[bold green]You:[/bold green] ").strip()
            if not question:
                continue

            console.print(Rule(style="dim"))
            answer = await ask_with_mcp(question, verbose=True)
            console.print(f"\n[bold blue]Claude:[/bold blue] {answer}\n")
            console.print(Rule(style="dim"))

        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/dim]")
            break


async def run_demo() -> None:
    """Run a scripted demo showing MCP in action across all tools."""
    console.print(Panel.fit(
        "[bold cyan]MCP Explained — Scripted Demo[/bold cyan]\n"
        "[dim]Demonstrating all 7 tools via Claude + MCP[/dim]",
        border_style="cyan",
    ))

    demo_questions = [
        ("Calculator", "What is the surface area of a sphere with radius 7? Use the formula 4 * pi * r^2."),
        ("Weather", "What's the weather in Tokyo and London right now?"),
        ("Notes", "Save a note with key 'demo-run' containing: MCP demo ran successfully on this date."),
        ("Notes", "List all my saved notes."),
        ("Word Count", "Count the words in: 'Model Context Protocol is an open standard that enables AI models to securely connect with local and remote resources.'"),
        ("DateTime", "What is today's date?"),
    ]

    for label, question in demo_questions:
        console.print(f"\n[bold yellow]── {label} Tool ──[/bold yellow]")
        console.print(f"[bold green]Q:[/bold green] {question}")
        answer = await ask_with_mcp(question, verbose=True)
        console.print(f"[bold blue]A:[/bold blue] {answer}")
        console.print()


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Question passed as command-line argument
        user_question = " ".join(sys.argv[1:])
        console.print(f"[bold green]Question:[/bold green] {user_question}\n")
        answer = asyncio.run(ask_with_mcp(user_question, verbose=True))
        console.print(f"\n[bold blue]Claude:[/bold blue] {answer}")
    elif "--demo" in sys.argv:
        asyncio.run(run_demo())
    else:
        asyncio.run(interactive_mode())
