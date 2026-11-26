"""
Report Generator (Core Requirement #7)
========================================
Generates honest quality reports that state what works and what still fails.
A factory that claims 100% is suspicious; a factory that explains its 78% is hired.
"""

import json
from pathlib import Path
from datetime import datetime

from forgeai.models import ForgeAIReport


def generate_report(report: ForgeAIReport, output_dir: str) -> str:
    """
    Generate a comprehensive, honest quality report and save all pipeline artifacts.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    final_sc = report.scorecards[-1] if report.scorecards else None

    md = []
    md.append("# 🏭 ForgeAI Quality Report")
    md.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**Agent:** {report.agent_definition.name}")
    md.append(f"**Final Score:** {report.final_score:.1%}")
    md.append(f"**Total Iterations:** {report.total_iterations}")
    md.append(f"**Total Tokens Used:** {report.total_tokens_used:,}")

    # 1. Requirements Summary
    md.append("\n## 📋 Requirements Summary")
    md.append(f"- **Scope:** {report.requirements.scope}")
    md.append(f"- **Audience:** {report.requirements.audience}")
    md.append(f"- **Tone:** {report.requirements.tone}")
    md.append(f"- **Must-answer topics:** {', '.join(report.requirements.must_answer_topics)}")
    md.append(f"- **Must-refuse topics:** {', '.join(report.requirements.must_refuse_topics)}")
    if report.requirements.required_capabilities:
        md.append(f"- **Required capabilities:** {', '.join(report.requirements.required_capabilities)}")
    if report.requirements.document_coverage:
        md.append("- **Document coverage:**")
        for cov in report.requirements.document_coverage:
            md.append(f"  - {cov}")

    # 2. Groundability Findings
    md.append("\n## 🛡️ Groundability Findings")
    if report.requirements.groundability_warnings or report.requirements.unsupported_requirements:
        for warning in report.requirements.groundability_warnings:
            md.append(f"- ⚠️ {warning}")
        for unsup in report.requirements.unsupported_requirements:
            if unsup not in report.requirements.groundability_warnings:
                md.append(f"- 🚫 Unsupported: {unsup}")
    else:
        md.append("- All requested capabilities are supported by the supplied documents.")

    # 3. Generated Agent Definition & Selected Tools
    md.append("\n## 🤖 Generated Agent Definition & Selected Tools")
    md.append(f"- **Agent Name:** {report.agent_definition.name}")
    md.append(f"- **Scope:** {report.agent_definition.scope or report.requirements.scope}")
    md.append(f"- **Selected Tools:** {', '.join(report.agent_definition.tools) if report.agent_definition.tools else 'None (pure RAG)'}")
    md.append(f"- **Documents:** {', '.join(report.agent_definition.document_list) if report.agent_definition.document_list else 'Loaded from folder'}")
    md.append(f"- **Citation Behavior:** {report.agent_definition.citation_behavior}")
    rc = report.agent_definition.retrieval_config
    md.append(
        f"- **Retrieval Config:** `chunk_size={rc.chunk_size}`, `chunk_overlap={rc.chunk_overlap}`, "
        f"`top_k={rc.top_k}`, `score_threshold={rc.score_threshold}`"
    )
    oc = report.agent_definition.output_contract
    md.append(
        f"- **Output Contract:** `format={oc.format}`, `max_length={oc.max_length}`, "
        f"`must_cite_sources={oc.must_cite_sources}`"
    )
    md.append(f"- **Refusal Template:** `{oc.refusal_template}`")

    # 4. Evaluation-Set Summary
    md.append("\n## 📝 Evaluation-Set Summary")
    cat_counts = {}
    for c in report.eval_set.cases:
        cat_counts[c.case_type.value] = cat_counts.get(c.case_type.value, 0) + 1
    md.append(f"- **Total Cases:** {len(report.eval_set.cases)}")
    for cat, cnt in sorted(cat_counts.items()):
        md.append(f"  - `{cat}`: {cnt} cases")

    # 5. Score per Category
    if final_sc and final_sc.category_scores:
        md.append("\n## 📈 Score per Category (Final Iteration)")
        md.append("| Category | Average Score |")
        md.append("|----------|---------------|")
        for cat, val in sorted(final_sc.category_scores.items()):
            md.append(f"| {cat} | {val:.1%} |")

    # 6. Iteration-by-Iteration Scorecard
    md.append("\n## 📊 Iteration-by-Iteration Scorecard")
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

    if len(report.scorecards) > 1:
        md.append("\n### Score Progression")
        md.append("```")
        for sc in report.scorecards:
            bar_len = int(sc.score * 40)
            bar = "█" * bar_len + "░" * (40 - bar_len)
            md.append(f"Iteration {sc.iteration}: [{bar}] {sc.score:.1%}")
        md.append("```")

    # 7. Optimization Log
    if report.optimization_logs:
        md.append("\n## 🔧 Optimization Log")
        for log in report.optimization_logs:
            md.append(f"\n### Iteration {log.iteration}: {log.change_type} ({log.failure_category})")
            if log.diagnosis:
                md.append(f"- **Diagnosis:** {log.diagnosis}")
            md.append(f"- **Change Applied:** {log.description}")
            if log.reason:
                md.append(f"- **Reason:** {log.reason}")
            md.append(f"- **Cases Targeted:** {', '.join(log.failures_addressed) if log.failures_addressed else 'General improvement'}")
            md.append(f"- **Score before:** {log.score_before:.1%}")
            md.append(f"- **Score after:** {log.score_after:.1%}")
            improvement = log.score_after - log.score_before
            emoji = "📈" if improvement > 0 else "📉" if improvement < 0 else "➡️"
            md.append(f"- **Impact:** {emoji} {improvement:+.1%}")

    # 8. Per-Case Score Table
    if final_sc and final_sc.case_scores:
        md.append("\n## 🔍 Per-Case Score (Final Iteration)")
        md.append("| Case ID | Category | Score | Grounded | Correct | Failure Category | Question |")
        md.append("|---------|----------|-------|----------|---------|------------------|----------|")
        for cs in final_sc.case_scores:
            q_short = cs.question.replace("|", " ").replace("\n", " ")[:65]
            md.append(
                f"| {cs.case_id} | {cs.case_type.value} | {cs.score:.2f} | "
                f"{'Yes' if cs.is_grounded else 'No'} | {'Yes' if cs.is_correct else 'No'} | "
                f"{cs.failure_category.value} | {q_short} |"
            )

    # 9. Remaining Failures & Known Limitations (HONEST REPORTING)
    md.append("\n## ❌ Remaining Failures & Reasons")
    if report.known_failures:
        md.append(
            "The following issues remain unresolved. This is an honest assessment — "
            "understanding failures is more valuable than hiding them."
        )
        for failure in report.known_failures:
            md.append(f"- {failure}")
    else:
        md.append(
            "All evaluation cases met the passing threshold (≥ 0.70). However, real-world usage "
            "may still reveal edge cases outside the generated test suite."
        )

    md.append("\n## ⚠️ Known Limitations & Final Quality Conclusion")
    md.append(
        "- Static document knowledge base: information updated outside the document folder requires re-indexing.\n"
        "- Retrieval quality depends on chunk boundaries and semantic overlap.\n"
        f"- **Conclusion:** The agent achieved **{report.final_score:.1%}** across {len(report.eval_set.cases)} "
        f"evaluation cases over {report.total_iterations} iteration(s), with "
        f"{len(report.known_failures)} remaining failure(s) documented above."
    )

    if report.recommendations:
        md.append("\n## 💡 Recommendations for Improvement")
        for rec in report.recommendations:
            md.append(f"- {rec}")

    report_text = "\n".join(md)
    _save_artifacts(report, output_path, report_text)
    return report_text


def _save_artifacts(report: ForgeAIReport, output_path: Path, report_text: str):
    """Save all artifacts to the output directory."""
    (output_path / "quality_report.md").write_text(report_text, encoding="utf-8")

    # Requirements artifacts
    (output_path / "requirements.json").write_text(
        report.requirements.model_dump_json(indent=2), encoding="utf-8"
    )
    req_md = [
        "# Requirements Document",
        f"**Scope:** {report.requirements.scope}",
        f"**Audience:** {report.requirements.audience}",
        f"**Tone:** {report.requirements.tone}",
        "\n## Must-Answer Topics",
        *[f"- {t}" for t in report.requirements.must_answer_topics],
        "\n## Must-Refuse Topics",
        *[f"- {t}" for t in report.requirements.must_refuse_topics],
        "\n## Groundability Warnings",
        *([f"- {w}" for w in report.requirements.groundability_warnings] or ["- None"]),
    ]
    (output_path / "requirements.md").write_text("\n".join(req_md), encoding="utf-8")

    (output_path / "clarifications.json").write_text(
        json.dumps(report.requirements.clarifications, indent=2), encoding="utf-8"
    )
    (output_path / "groundability.json").write_text(
        json.dumps({
            "groundability_warnings": report.requirements.groundability_warnings,
            "unsupported_requirements": report.requirements.unsupported_requirements,
            "document_coverage": report.requirements.document_coverage,
        }, indent=2),
        encoding="utf-8"
    )

    # Agent definition artifacts
    (output_path / "agent_definition.json").write_text(
        report.agent_definition.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_path / "system_prompt.txt").write_text(
        report.agent_definition.system_prompt, encoding="utf-8"
    )
    (output_path / "retrieval_config.json").write_text(
        report.agent_definition.retrieval_config.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_path / "output_contract.json").write_text(
        report.agent_definition.output_contract.model_dump_json(indent=2), encoding="utf-8"
    )

    # Evaluation artifacts
    (output_path / "eval_set.json").write_text(
        report.eval_set.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_path / "eval_generation_prompt.txt").write_text(
        report.eval_set.generation_prompt, encoding="utf-8"
    )

    # Scorecards, raw responses, judge results, optimization logs
    scorecards_data = [sc.model_dump() for sc in report.scorecards]
    (output_path / "scorecards.json").write_text(
        json.dumps(scorecards_data, indent=2, default=str), encoding="utf-8"
    )

    if report.scorecards:
        final_sc = report.scorecards[-1]
        raw_responses = [
            {
                "case_id": cs.case_id,
                "question": cs.question,
                "agent_response": cs.agent_response,
                "retrieved_chunks": cs.retrieved_chunks,
            }
            for cs in final_sc.case_scores
        ]
        (output_path / "raw_responses.json").write_text(
            json.dumps(raw_responses, indent=2, default=str), encoding="utf-8"
        )
        judge_results = [
            {
                "case_id": cs.case_id,
                "case_type": cs.case_type.value,
                "is_grounded": cs.is_grounded,
                "is_correct": cs.is_correct,
                "correctly_refused": cs.correctly_refused,
                "score": cs.score,
                "failure_category": cs.failure_category.value,
                "failure_explanation": cs.failure_explanation,
            }
            for cs in final_sc.case_scores
        ]
        (output_path / "judge_results.json").write_text(
            json.dumps(judge_results, indent=2, default=str), encoding="utf-8"
        )

    if report.optimization_logs:
        logs_data = [log.model_dump() for log in report.optimization_logs]
        (output_path / "optimization_logs.json").write_text(
            json.dumps(logs_data, indent=2, default=str), encoding="utf-8"
        )

    (output_path / "full_report.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
