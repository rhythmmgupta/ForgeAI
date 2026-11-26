"""
Report Generator (Core Requirement #7)
========================================
Generates honest quality reports that state what works and what still fails.
A factory that claims 100% is suspicious; a factory that explains its 78% is hired.
"""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from forgeai.models import ForgeAIReport, IterationScorecard


def generate_report(report: ForgeAIReport, output_dir: str) -> str:
    """
    Generate a comprehensive, honest quality report.
    
    Returns the report as a formatted markdown string and saves artifacts.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Build markdown report
    md = []
    md.append("# 🏭 ForgeAI Quality Report")
    md.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**Agent:** {report.agent_definition.name}")
    md.append(f"**Final Score:** {report.final_score:.1%}")
    md.append(f"**Total Iterations:** {report.total_iterations}")
    md.append(f"**Total Tokens Used:** {report.total_tokens_used:,}")

    # Requirements summary
    md.append("\n## 📋 Requirements Summary")
    md.append(f"- **Scope:** {report.requirements.scope}")
    md.append(f"- **Audience:** {report.requirements.audience}")
    md.append(f"- **Tone:** {report.requirements.tone}")
    md.append(f"- **Must-answer topics:** {', '.join(report.requirements.must_answer_topics)}")
    md.append(f"- **Must-refuse topics:** {', '.join(report.requirements.must_refuse_topics)}")

    if report.requirements.groundability_warnings:
        md.append("\n### ⚠️ Groundability Warnings")
        for warning in report.requirements.groundability_warnings:
            md.append(f"- {warning}")

    # Iteration scorecards
    md.append("\n## 📊 Iteration Scorecards")
    for sc in report.scorecards:
        md.append(f"\n### Iteration {sc.iteration}")
        md.append(f"- **Score:** {sc.score:.1%}")
        md.append(f"- **Passed:** {sc.passed}/{sc.total_cases}")
        md.append(f"- **Failed:** {sc.failed}/{sc.total_cases}")
        if sc.failure_breakdown:
            md.append("- **Failure Breakdown:**")
            for cat, count in sc.failure_breakdown.items():
                md.append(f"  - {cat}: {count}")
        if sc.changes_made:
            md.append("- **Changes Applied:**")
            for change in sc.changes_made:
                md.append(f"  - {change}")

    # Score progression
    if len(report.scorecards) > 1:
        md.append("\n### Score Progression")
        md.append("```")
        for sc in report.scorecards:
            bar_len = int(sc.score * 40)
            bar = "█" * bar_len + "░" * (40 - bar_len)
            md.append(f"Iteration {sc.iteration}: [{bar}] {sc.score:.1%}")
        md.append("```")

    # Optimization log
    if report.optimization_logs:
        md.append("\n## 🔧 Optimization Log")
        for log in report.optimization_logs:
            md.append(f"\n### Iteration {log.iteration}: {log.change_type}")
            md.append(f"- **Change:** {log.description}")
            md.append(f"- **Addressed failures:** {', '.join(log.failures_addressed) if log.failures_addressed else 'General improvement'}")
            md.append(f"- **Score before:** {log.score_before:.1%}")
            md.append(f"- **Score after:** {log.score_after:.1%}")
            improvement = log.score_after - log.score_before
            emoji = "📈" if improvement > 0 else "📉" if improvement < 0 else "➡️"
            md.append(f"- **Impact:** {emoji} {improvement:+.1%}")

    # Prompt tournament results (stretch goal)
    if report.prompt_tournament_results:
        md.append("\n## 🏆 Prompt Tournament Results")
        tournament = report.prompt_tournament_results
        if "candidates" in tournament:
            for cand in tournament["candidates"]:
                md.append(f"- **{cand.get('name', 'Unknown')}:** {cand.get('score', 0):.1%}")
        if "winner" in tournament:
            md.append(f"\n**Winner:** {tournament['winner']}")

    # Known failures (HONEST REPORTING)
    md.append("\n## ❌ Known Failures & Limitations")
    if report.known_failures:
        md.append(
            "The following issues remain unresolved. This is an honest assessment — "
            "understanding failures is more valuable than hiding them."
        )
        for failure in report.known_failures:
            md.append(f"- {failure}")
    else:
        md.append(
            "No known failures at this time. However, real-world usage may reveal "
            "edge cases not covered by the evaluation set."
        )

    # Recommendations
    if report.recommendations:
        md.append("\n## 💡 Recommendations for Improvement")
        for rec in report.recommendations:
            md.append(f"- {rec}")

    # Agent definition summary
    md.append("\n## 🤖 Final Agent Definition")
    md.append(f"- **System Prompt Length:** {len(report.agent_definition.system_prompt)} chars")
    md.append(f"- **Tools Attached:** {', '.join(report.agent_definition.tools) if report.agent_definition.tools else 'None'}")
    md.append(f"- **Retrieval Config:**")
    rc = report.agent_definition.retrieval_config
    md.append(f"  - chunk_size: {rc.chunk_size}")
    md.append(f"  - chunk_overlap: {rc.chunk_overlap}")
    md.append(f"  - top_k: {rc.top_k}")
    md.append(f"  - score_threshold: {rc.score_threshold}")

    report_text = "\n".join(md)

    # Save artifacts
    _save_artifacts(report, output_path, report_text)

    return report_text


def _save_artifacts(report: ForgeAIReport, output_path: Path, report_text: str):
    """Save all artifacts to the output directory."""
    # Save report
    (output_path / "quality_report.md").write_text(report_text, encoding="utf-8")

    # Save agent definition
    (output_path / "agent_definition.json").write_text(
        report.agent_definition.model_dump_json(indent=2), encoding="utf-8"
    )

    # Save requirements
    (output_path / "requirements.json").write_text(
        report.requirements.model_dump_json(indent=2), encoding="utf-8"
    )

    # Save eval set
    (output_path / "eval_set.json").write_text(
        report.eval_set.model_dump_json(indent=2), encoding="utf-8"
    )

    # Save scorecards
    scorecards_data = [sc.model_dump() for sc in report.scorecards]
    (output_path / "scorecards.json").write_text(
        json.dumps(scorecards_data, indent=2, default=str), encoding="utf-8"
    )

    # Save optimization logs
    if report.optimization_logs:
        logs_data = [log.model_dump() for log in report.optimization_logs]
        (output_path / "optimization_logs.json").write_text(
            json.dumps(logs_data, indent=2, default=str), encoding="utf-8"
        )

    # Save full report as JSON
    (output_path / "full_report.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
