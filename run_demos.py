#!/usr/bin/env python3
"""
Run both ForgeAI demos end-to-end and commit all artifacts.
Core Requirement #9: Two full demonstrations.
"""

import sys
import json
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from forgeai.config import ForgeAIConfig, LLMConfig, BudgetConfig
from forgeai.pipeline import ForgeAIPipeline
from rich.console import Console

console = Console()


def run_all_demos():
    """Run both demos and produce complete artifacts."""
    
    config = ForgeAIConfig(
        llm=LLMConfig(),
        budget=BudgetConfig(max_iterations=3),
    )

    demos = [
        {
            "name": "HR Policy Assistant",
            "brief_file": "forgeai/demos/hr_policy_assistant/brief.txt",
            "docs": "forgeai/demos/hr_policy_assistant/documents",
            "output": "forgeai/demos/hr_policy_assistant/artifacts"
        },
        {
            "name": "Ship Spares Procurement Assistant",
            "brief_file": "forgeai/demos/ship_spares_assistant/brief.txt",
            "docs": "forgeai/demos/ship_spares_assistant/documents",
            "output": "forgeai/demos/ship_spares_assistant/artifacts"
        }
    ]

    reports = []

    for demo in demos:
        console.print(f"\n{'='*60}")
        console.print(f"[bold cyan]DEMO: {demo['name']}[/bold cyan]")
        console.print(f"{'='*60}\n")

        brief = Path(demo["brief_file"]).read_text().strip()
        
        # Clear previous artifacts
        output_path = Path(demo["output"])
        if output_path.exists():
            shutil.rmtree(output_path)

        pipeline = ForgeAIPipeline(config)
        report = pipeline.run(
            brief=brief,
            doc_folder=demo["docs"],
            output_dir=demo["output"],
            auto_mode=True,
            run_tournament=True,
        )

        # If this is HR policy assistant, also run stretch goals: Baseline & Regression
        if demo["name"] == "HR Policy Assistant":
            console.print("\n[bold magenta]Running Stretch Goal: Factory vs Human Baseline...[/bold magenta]")
            from forgeai.core.baseline_comparator import BaselineComparator, HUMAN_BASELINE_HR_AGENT
            comparator = BaselineComparator(config)
            comparator.compare(
                factory_definition=report.agent_definition,
                human_definition=HUMAN_BASELINE_HR_AGENT,
                eval_set=report.eval_set,
                doc_folder=demo["docs"],
                output_dir=demo["output"]
            )
            console.print("[green]✅ Baseline comparison artifact created![/green]")

            console.print("\n[bold magenta]Running Stretch Goal: Document Regression Mode...[/bold magenta]")
            from forgeai.core.regression_runner import RegressionRunner
            reg_runner = RegressionRunner(config)
            last_sc = report.scorecards[-1] if report.scorecards else None
            reg_runner.run_regression_test(
                regenerated_agent=report.agent_definition,
                old_eval_set=report.eval_set,
                updated_doc_folder=demo["docs"],
                baseline_scorecard=last_sc,
                output_dir=demo["output"]
            )
            console.print("[green]✅ Regression test artifact created![/green]")

        reports.append({
            "name": demo["name"],
            "score": report.final_score,
            "iterations": report.total_iterations,
            "failures": len(report.known_failures),
            "output": demo["output"]
        })

        console.print(f"\n[green]✅ {demo['name']}: Score {report.final_score:.1%}[/green]")

    # Summary
    console.print(f"\n{'='*60}")
    console.print("[bold green]ALL DEMOS COMPLETE[/bold green]")
    console.print(f"{'='*60}")
    
    for r in reports:
        console.print(
            f"  {r['name']}: {r['score']:.1%} "
            f"({r['iterations']} iterations, {r['failures']} known failures)"
        )
        console.print(f"  → Artifacts: {r['output']}")
    

if __name__ == "__main__":
    run_all_demos()
