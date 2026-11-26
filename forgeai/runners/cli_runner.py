"""
CLI Chat Runner
================
Minimal CLI-based chat runner for interacting with generated agents.
Core Requirement #8: The generated agent must actually run.
"""

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from forgeai.config import ForgeAIConfig, LLMConfig, EmbeddingConfig
from forgeai.models import AgentDefinition
from forgeai.runners.agent_runner import AgentRunner
from forgeai.tools.registry import ToolRegistry


def run_cli_chat(
    definition_path: str,
    doc_folder: str,
    config: ForgeAIConfig = None
):
    """Run an interactive CLI chat session with a generated agent."""
    console = Console()

    if config is None:
        config = ForgeAIConfig()

    # Load agent definition
    console.print("[bold cyan]Loading agent definition...[/bold cyan]")
    with open(definition_path, "r") as f:
        data = json.load(f)
    definition = AgentDefinition(**data)

    # Create runner
    console.print("[bold cyan]Building vector store from documents...[/bold cyan]")
    runner = AgentRunner(
        agent_definition=definition,
        llm_config=config.llm,
        embedding_config=config.embedding,
        doc_folder=doc_folder,
        tool_registry=ToolRegistry()
    )

    # Display agent info
    console.print(Panel(
        f"[bold green]{definition.name}[/bold green]\n\n"
        f"Tools: {', '.join(definition.tools) if definition.tools else 'None'}\n"
        f"Retrieval: top_k={definition.retrieval_config.top_k}, "
        f"chunk_size={definition.retrieval_config.chunk_size}\n"
        f"Format: {definition.output_contract.format}",
        title="🤖 Agent Ready",
        border_style="green"
    ))

    console.print("[dim]Type 'quit' or 'exit' to end the chat. Type 'clear' to reset history.[/dim]\n")

    while True:
        try:
            question = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold red]Goodbye![/bold red]")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit"):
            console.print("[bold red]Goodbye![/bold red]")
            break
        if question.lower() == "clear":
            runner.reset_history()
            console.print("[dim]Chat history cleared.[/dim]")
            continue

        # Get response
        with console.status("[bold green]Thinking..."):
            answer, chunks = runner.query(question, return_context=True)

        # Display answer
        console.print(f"\n[bold cyan]Agent:[/bold cyan]")
        console.print(Markdown(answer))

        # Show tools & sources used
        if getattr(runner, "last_tools_used", None):
            console.print(f"[dim]🔧 Tools invoked: {', '.join(runner.last_tools_used)}[/dim]")
        if chunks:
            console.print(f"\n[dim]📄 Sources used ({len(chunks)} chunks):[/dim]")
            for i, chunk in enumerate(chunks[:3], 1):
                preview = chunk[:150].replace("\n", " ")
                console.print(f"[dim]  {i}. {preview}...[/dim]")

        console.print()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m forgeai.runners.cli_runner <definition.json> <doc_folder>")
        sys.exit(1)

    run_cli_chat(sys.argv[1], sys.argv[2])
