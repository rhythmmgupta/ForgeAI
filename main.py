#!/usr/bin/env python3
"""
ForgeAI — Main CLI Entry Point
Run the ForgeAI pipeline from the command line.

Usage:
    python main.py --brief "your brief" --docs ./documents --output ./output
    python main.py --brief-file brief.txt --docs ./documents --output ./output
    python main.py --demo hr        # Run HR policy assistant demo
    python main.py --demo spares    # Run ship spares assistant demo
    python main.py --chat <definition.json> --docs ./documents
    python main.py --ui             # Launch Streamlit UI
"""

import argparse
import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def run_pipeline(args):
    """Run the ForgeAI pipeline."""
    from forgeai.config import ForgeAIConfig, LLMConfig, BudgetConfig
    from forgeai.pipeline import ForgeAIPipeline

    # Get brief
    if args.brief_file:
        brief = Path(args.brief_file).read_text().strip()
    elif args.brief:
        brief = args.brief
    else:
        print("Error: Provide --brief or --brief-file")
        sys.exit(1)

    # Validate docs folder
    if not Path(args.docs).exists():
        print(f"Error: Document folder not found: {args.docs}")
        sys.exit(1)

    # Build config
    config = ForgeAIConfig(
        llm=LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "groq"),
            model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
        ),
        budget=BudgetConfig(max_iterations=args.max_iterations),
        verbose=True
    )

    # Run pipeline
    pipeline = ForgeAIPipeline(config)
    report = pipeline.run(
        brief=brief,
        doc_folder=args.docs,
        output_dir=args.output,
        auto_mode=args.auto,
        human_checkpoint=args.human_checkpoint,
        run_tournament=args.tournament,
    )

    print(f"\n✅ Pipeline complete! Final score: {report.final_score:.1%}")
    print(f"📁 Artifacts saved to: {args.output}")


def run_demo(demo_name: str, output_base: str = "output"):
    """Run a predefined demo."""
    from forgeai.config import ForgeAIConfig, LLMConfig, BudgetConfig
    from forgeai.pipeline import ForgeAIPipeline

    demos = {
        "hr": {
            "brief_file": "forgeai/demos/hr_policy_assistant/brief.txt",
            "docs": "forgeai/demos/hr_policy_assistant/documents",
            "output": f"{output_base}/demo_hr_policy"
        },
        "spares": {
            "brief_file": "forgeai/demos/ship_spares_assistant/brief.txt",
            "docs": "forgeai/demos/ship_spares_assistant/documents",
            "output": f"{output_base}/demo_ship_spares"
        }
    }

    if demo_name not in demos:
        print(f"Unknown demo: {demo_name}. Available: {', '.join(demos.keys())}")
        sys.exit(1)

    demo = demos[demo_name]
    brief = Path(demo["brief_file"]).read_text().strip()
    
    print(f"🏭 Running demo: {demo_name}")
    print(f"📄 Brief: {brief[:100]}...")
    print(f"📁 Documents: {demo['docs']}")

    config = ForgeAIConfig(
        llm=LLMConfig(),
        budget=BudgetConfig(max_iterations=3),
    )

    pipeline = ForgeAIPipeline(config)
    report = pipeline.run(
        brief=brief,
        doc_folder=demo["docs"],
        output_dir=demo["output"],
        auto_mode=True,
        run_tournament=True,
    )

    print(f"\n✅ Demo '{demo_name}' complete! Score: {report.final_score:.1%}")
    print(f"📁 Artifacts: {demo['output']}")
    return report


def run_chat(args):
    """Run the CLI chat runner."""
    from forgeai.runners.cli_runner import run_cli_chat
    from forgeai.config import ForgeAIConfig

    config = ForgeAIConfig()
    run_cli_chat(args.chat, args.docs, config)


def run_baseline(args):
    """Run the Factory vs Human Baseline comparison (Stretch Goal)."""
    from forgeai.core.baseline_comparator import BaselineComparator, HUMAN_BASELINE_HR_AGENT
    from forgeai.models import AgentDefinition, EvalSet
    from forgeai.config import ForgeAIConfig

    print("⚔️ Running Factory vs Human Baseline Comparison...")
    agent_path = Path(args.baseline)
    eval_set_path = Path(args.eval_set or agent_path.parent / "eval_set.json")
    doc_folder = args.docs or "forgeai/demos/hr_policy_assistant/documents"

    if not agent_path.exists():
        print(f"Error: Agent definition not found at {agent_path}")
        sys.exit(1)
    if not eval_set_path.exists():
        print(f"Error: Eval set not found at {eval_set_path}")
        sys.exit(1)

    factory_def = AgentDefinition(**json.loads(agent_path.read_text(encoding="utf-8")))
    eval_set = EvalSet(**json.loads(eval_set_path.read_text(encoding="utf-8")))

    comparator = BaselineComparator(ForgeAIConfig())
    res = comparator.compare(
        factory_definition=factory_def,
        human_definition=HUMAN_BASELINE_HR_AGENT,
        eval_set=eval_set,
        doc_folder=doc_folder,
        output_dir=args.output
    )
    print(f"\n✅ Comparison Complete!")
    print(f"Factory Score: {res['factory_score']:.1%} | Human Score: {res['human_score']:.1%}")
    print(f"📄 Full report saved to: {res['report_path']}")


def run_regression(args):
    """Run Document Regression Mode (Stretch Goal)."""
    from forgeai.core.regression_runner import RegressionRunner
    from forgeai.models import AgentDefinition, EvalSet, IterationScorecard
    from forgeai.config import ForgeAIConfig

    print("🔄 Running Document Regression Mode...")
    agent_path = Path(args.regression)
    eval_set_path = Path(args.eval_set or agent_path.parent / "eval_set.json")
    scorecards_path = agent_path.parent / "scorecards.json"
    doc_folder = args.docs or "forgeai/demos/hr_policy_assistant/documents"

    if not agent_path.exists() or not eval_set_path.exists():
        print("Error: Agent definition or eval set not found.")
        sys.exit(1)

    factory_def = AgentDefinition(**json.loads(agent_path.read_text(encoding="utf-8")))
    eval_set = EvalSet(**json.loads(eval_set_path.read_text(encoding="utf-8")))

    baseline_scorecard = None
    if scorecards_path.exists():
        sc_data = json.loads(scorecards_path.read_text(encoding="utf-8"))
        if sc_data:
            baseline_scorecard = IterationScorecard(**sc_data[-1])

    reg_runner = RegressionRunner(ForgeAIConfig())
    res = reg_runner.run_regression_test(
        regenerated_agent=factory_def,
        old_eval_set=eval_set,
        updated_doc_folder=doc_folder,
        baseline_scorecard=baseline_scorecard,
        output_dir=args.output
    )
    print(f"\n✅ Regression Analysis Complete!")
    print(f"Post-Update Score: {res['new_score']:.1%} | Regressions: {res['regressions_count']}")
    print(f"📄 Full report saved to: {res['report_path']}")


def run_ui():
    """Launch the Streamlit UI."""
    import subprocess
    ui_path = Path(__file__).parent / "forgeai" / "ui" / "streamlit_app.py"
    subprocess.run(["streamlit", "run", str(ui_path)])


def main():
    parser = argparse.ArgumentParser(
        description="ForgeAI — The Agent That Builds Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --demo hr                    Run HR policy demo
  python main.py --demo spares                Run ship spares demo
  python main.py --brief "..." --docs ./docs  Custom run
  python main.py --chat output/agent.json --docs ./docs  Chat with agent
  python main.py --baseline output/agent_definition.json  Factory vs Human Baseline
  python main.py --regression output/agent_definition.json Document Regression Mode
  python main.py --ui                         Launch Streamlit UI
        """
    )

    # Mutually exclusive modes
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--brief", help="Agent brief (one paragraph)")
    group.add_argument("--brief-file", help="Path to file containing the brief")
    group.add_argument("--demo", choices=["hr", "spares"], help="Run a predefined demo")
    group.add_argument("--chat", help="Chat with a generated agent (path to definition.json)")
    group.add_argument("--baseline", help="Compare agent vs human baseline (path to agent_definition.json)")
    group.add_argument("--regression", help="Run regression mode (path to agent_definition.json)")
    group.add_argument("--ui", action="store_true", help="Launch Streamlit UI")

    # Pipeline options
    parser.add_argument("--docs", help="Path to document folder")
    parser.add_argument("--eval-set", help="Path to eval_set.json for baseline/regression modes")
    parser.add_argument("--output", default="output", help="Output directory for artifacts")
    parser.add_argument("--max-iterations", type=int, default=3, help="Max optimization iterations")
    parser.add_argument("--auto", action="store_true", default=True, help="Auto-answer clarifying questions")
    parser.add_argument("--interactive", dest="auto", action="store_false", help="Interactive interview mode")
    parser.add_argument("--tournament", action="store_true", default=True, help="Run prompt tournament")
    parser.add_argument("--no-tournament", dest="tournament", action="store_false")
    parser.add_argument("--human-checkpoint", action="store_true", help="Pause for human review")

    args = parser.parse_args()

    if args.ui:
        run_ui()
    elif args.demo:
        run_demo(args.demo, args.output)
    elif args.baseline:
        run_baseline(args)
    elif args.regression:
        run_regression(args)
    elif args.chat:
        if not args.docs:
            parser.error("--chat requires --docs")
        run_chat(args)
    else:
        if not args.docs:
            parser.error("--brief/--brief-file requires --docs")
        run_pipeline(args)


if __name__ == "__main__":
    main()
