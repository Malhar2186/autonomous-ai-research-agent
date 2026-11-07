import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt

from research_agent.agent.researcher import AutonomousResearcher
from research_agent.config import config

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Autonomous AI Research Agent - Multi-tool Web & Academic Deep Research System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "topic",
        nargs="?",
        default=None,
        help="The research topic or question to investigate (prompted interactively if omitted).",
    )
    parser.add_argument(
        "--depth",
        choices=["quick", "standard", "deep"],
        default="standard",
        help="Depth of research: quick (fast overview), standard (balanced deep dive), deep (extensive multi-query with gap reflection).",
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "openai", "groq", "ollama"],
        default=config.provider,
        help="LLM provider backend.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Specific model name (defaults to provider's configured model in .env).",
    )
    parser.add_argument(
        "--academic",
        action="store_true",
        help="Include academic papers search (arXiv) alongside web search.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./output"),
        help="Directory to save the generated markdown research reports.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    topic = args.topic
    if not topic:
        console.print("[bold cyan]🤖 Welcome to the Autonomous AI Research Agent![/bold cyan]\n")
        topic = Prompt.ask("[bold green]Enter your research topic or question[/bold green]")
        if not topic.strip():
            console.print("[red]Topic cannot be empty. Exiting.[/red]")
            sys.exit(1)

        # Allow user to choose depth interactively if not passed via CLI
        depth = Prompt.ask(
            "[bold yellow]Select research depth[/bold yellow]",
            choices=["quick", "standard", "deep"],
            default=args.depth,
        )
    else:
        depth = args.depth

    agent = AutonomousResearcher(
        provider=args.provider,
        model=args.model,
        output_dir=args.output_dir,
    )

    try:
        report_path = agent.run(
            topic=topic,
            depth=depth,
            include_academic=args.academic,
        )
        console.print(f"\n[bold green]Done! You can review your report at:[/bold green] [underline]{report_path}[/underline]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Research aborted by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Error during research execution: {e}[/red]")
        raise e


if __name__ == "__main__":
    main()

