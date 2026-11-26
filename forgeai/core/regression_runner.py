"""
Document Regression Mode (Stretch Goal)
========================================
Detects and diagnoses what breaks when underlying knowledge documents change.
Re-runs historical evaluation suites against regenerated agents, tracking
regressions, fact invalidations, and altered answers.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from forgeai.models import (
    AgentDefinition, EvalSet, IterationScorecard, CaseScore
)
from forgeai.config import ForgeAIConfig
from forgeai.runners.agent_runner import AgentRunner
from forgeai.core.judge import Judge
from forgeai.core.document_processor import load_documents, chunk_documents, create_vector_store
from forgeai.tools.registry import ToolRegistry


class RegressionRunner:
    """
    Stretch Goal: Regression Mode
    Re-runs historical evaluation suites against updated documents and regenerated agents.
    Pinpoints exactly what broke and why.
    """

    def __init__(self, config: ForgeAIConfig = None):
        self.config = config or ForgeAIConfig()
        self.judge = Judge(self.config.llm)
        self.tool_registry = ToolRegistry()

    def run_regression_test(
        self,
        regenerated_agent: AgentDefinition,
        old_eval_set: EvalSet,
        updated_doc_folder: str,
        baseline_scorecard: Optional[IterationScorecard] = None,
        output_dir: str = "output/regression"
    ) -> Dict[str, Any]:
        """
        Re-run the old eval set against the updated agent and document folder.
        """
        documents = load_documents(updated_doc_folder)
        chunks = chunk_documents(
            documents,
            chunk_size=regenerated_agent.retrieval_config.chunk_size,
            chunk_overlap=regenerated_agent.retrieval_config.chunk_overlap
        )
        vector_store = create_vector_store(chunks, self.config.embedding)

        runner = AgentRunner(
            agent_definition=regenerated_agent,
            llm_config=self.config.llm,
            embedding_config=self.config.embedding,
            doc_folder=updated_doc_folder,
            tool_registry=self.tool_registry
        )

        responses = []
        contexts = []

        for case in old_eval_set.cases:
            try:
                retrieved = vector_store.similarity_search(
                    case.question, k=regenerated_agent.retrieval_config.top_k
                )
                context_chunks = [d.page_content for d in retrieved]
                ans, _ = runner.query(case.question)
                responses.append(ans)
                contexts.append(context_chunks)
            except Exception as e:
                responses.append(f"Error: {str(e)}")
                contexts.append([])

        new_scorecard = self.judge.score_all(
            old_eval_set.cases, responses, contexts, iteration=0
        )

        # Diagnose regressions
        regressions = []
        improvements = []
        stable = []

        baseline_scores = {}
        if baseline_scorecard:
            for cs in baseline_scorecard.case_scores:
                baseline_scores[cs.case_id] = cs

        for new_cs in new_scorecard.case_scores:
            old_cs = baseline_scores.get(new_cs.case_id)
            old_score = old_cs.score if old_cs else 1.0  # assume previously passing if not provided

            score_diff = new_cs.score - old_score

            item = {
                "case_id": new_cs.case_id,
                "question": new_cs.question,
                "case_type": new_cs.case_type.value,
                "old_score": old_score,
                "new_score": new_cs.score,
                "failure_category": new_cs.failure_category.value,
                "failure_explanation": new_cs.failure_explanation or "Answer differed from historical expected facts.",
                "new_response": new_cs.agent_response[:300]
            }

            if score_diff < -0.15:
                regressions.append(item)
            elif score_diff > 0.15:
                improvements.append(item)
            else:
                stable.append(item)

        # Format report
        report_md = self._format_regression_report(
            old_scorecard=baseline_scorecard,
            new_scorecard=new_scorecard,
            regressions=regressions,
            improvements=improvements,
            total_cases=len(old_eval_set.cases),
            updated_doc_folder=updated_doc_folder
        )

        # Save artifacts
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "regression_report.md").write_text(report_md, encoding="utf-8")
        (out_path / "regression_report.json").write_text(
            json.dumps({
                "old_score": baseline_scorecard.score if baseline_scorecard else None,
                "new_score": new_scorecard.score,
                "regressions_count": len(regressions),
                "improvements_count": len(improvements),
                "stable_count": len(stable),
                "regressions": regressions,
                "improvements": improvements
            }, indent=2),
            encoding="utf-8"
        )

        return {
            "new_score": new_scorecard.score,
            "regressions_count": len(regressions),
            "regressions": regressions,
            "report_path": str(out_path / "regression_report.md")
        }

    def _format_regression_report(
        self,
        old_scorecard: Optional[IterationScorecard],
        new_scorecard: IterationScorecard,
        regressions: List[Dict],
        improvements: List[Dict],
        total_cases: int,
        updated_doc_folder: str
    ) -> str:
        old_score_str = f"{old_scorecard.score:.1%}" if old_scorecard else "N/A"
        lines = [
            "# 🔄 Document Regression Analysis Report",
            f"\n**Updated Document Folder:** `{updated_doc_folder}`",
            f"**Historical Eval Cases Evaluated:** `{total_cases}`",
            f"**Baseline Score:** `{old_score_str}` → **Post-Update Score:** `{new_scorecard.score:.1%}`",
            f"**Status:** {'⚠️ Regressions Detected' if regressions else '✅ No Regressions Detected'}\n",
            "## 📊 Score Impact Summary\n",
            "| Metric | Value |",
            "|---|---|",
            f"| Baseline Score | `{old_score_str}` |",
            f"| Post-Regeneration Score | `{new_scorecard.score:.1%}` |",
            f"| Regressed Cases | **{len(regressions)}** |",
            f"| Improved Cases | {len(improvements)} |",
            f"| Passed Cases | {new_scorecard.passed}/{new_scorecard.total_cases} |",
            "\n---\n",
            "## 🚨 What Broke (Regressions)\n"
        ]

        if not regressions:
            lines.append("No regressions detected! The updated documents did not break existing eval criteria.")
        else:
            lines.append("The following historical test cases broke due to document content modifications:\n")
            for reg in regressions:
                lines.append(f"### ❌ [{reg['case_id']}] {reg['question']}")
                lines.append(f"- **Type:** `{reg['case_type']}`")
                lines.append(f"- **Score Shift:** `{reg['old_score']:.2f}` → `{reg['new_score']:.2f}`")
                lines.append(f"- **Root Cause:** `{reg['failure_category']}`: {reg['failure_explanation']}")
                lines.append(f"- **Agent Output Snippet:**\n  > {reg['new_response'][:200]}...\n")

        if improvements:
            lines.append("\n---\n## 📈 Improvements Detected\n")
            for imp in improvements:
                lines.append(f"- **[{imp['case_id']}]**: Score improved from `{imp['old_score']:.2f}` to `{imp['new_score']:.2f}`")

        lines.extend([
            "\n---\n",
            "## 🛠️ Actionable Recommendations\n",
            "1. **Re-baseline Test Cases**: If document policies intentionally changed (e.g., policy updates or catalogue price changes), the evaluation generator must be rerun to synthesize new gold expected facts.\n",
            "2. **Check Chunk Overlap**: If failures are categorized as `retrieval_miss`, inspect if new document structure requires adjusting `chunk_size` or `top_k`."
        ])

        return "\n".join(lines)
