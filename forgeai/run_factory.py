"""
ForgeAI Factory CLI (`python -m forgeai.run_factory`)
=====================================================
Clean command for running ForgeAI on any unseen brief and document folder.

Usage:
    python -m forgeai.run_factory \
        --brief path/to/brief.txt \
        --documents path/to/documents \
        --output path/to/output
"""

import argparse
import os
import sys
from pathlib import Path

from forgeai.config import ForgeAIConfig, LLMConfig, BudgetConfig
from forgeai.pipeline import ForgeAIPipeline


def main():
    parser = argparse.ArgumentParser(
        prog="forgeai.run_factory",
        description="Run the ForgeAI autonomous agent factory on any brief and document folder."
    )
    parser.add_argument(
        "--brief", required=True,
        help="Path to a brief .txt/.md file OR an inline brief string."
    )
    parser.add_argument(
        "--documents", "--docs", dest="documents", required=True,
        help="Path to the folder containing source documents (.pdf, .csv, .txt, .md)."
    )
    parser.add_argument(
        "--output", default="output/unseen_run",
        help="Output directory for all generated artifacts (default: output/unseen_run)."
    )
    parser.add_argument(
        "--interactive", action="store_true",
        help="Answer clarification questions interactively via CLI."
    )
    parser.add_argument(
        "--human-checkpoint", action="store_true",
        help="Pause for human approval after generating requirements."
    )
    parser.add_argument(
        "--max-iterations", type=int, default=3,
        help="Maximum optimization iterations (1-3, default: 3)."
    )
    parser.add_argument(
        "--no-tournament", action="store_true",
        help="Disable the optional prompt tournament."
    )

    args = parser.parse_args()

    # Resolve brief (file path or inline string)
    brief_candidate = Path(args.brief)
    if brief_candidate.exists() and brief_candidate.is_file():
        brief_text = brief_candidate.read_text(encoding="utf-8").strip()
    else:
        brief_text = args.brief.strip()

    if not brief_text:
        print("Error: Brief cannot be empty.", file=sys.stderr)
        sys.exit(1)

    docs_path = Path(args.documents)
    if not docs_path.exists() or not docs_path.is_dir():
        print(f"Error: Document folder not found: {args.documents}", file=sys.stderr)
        sys.exit(1)

    config = ForgeAIConfig(
        llm=LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "groq"),
            model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
        ),
        budget=BudgetConfig(max_iterations=max(1, min(3, args.max_iterations))),
        verbose=True,
    )

    pipeline = ForgeAIPipeline(config)
    report = pipeline.run(
        brief=brief_text,
        doc_folder=str(docs_path),
        output_dir=args.output,
        auto_mode=not args.interactive,
        human_checkpoint=args.human_checkpoint,
        run_tournament=not args.no_tournament,
    )

    print(f"\nFactory complete! Final score: {report.final_score:.1%}")
    print(f"Artifacts saved to: {args.output}")


if __name__ == "__main__":
    main()
