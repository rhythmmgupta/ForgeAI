"""
Critic-Optimizer Loop (Core Requirement #6)
=============================================
Run evals → classify failures → apply targeted fixes → re-run.
Maximum 3 iterations. Every change is logged.
"""

import json
from typing import List, Dict, Tuple

try:
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    from langchain.schema import HumanMessage, SystemMessage

from forgeai.config import LLMConfig, get_llm, BudgetConfig
from forgeai.models import (
    AgentDefinition, IterationScorecard, CaseScore,
    FailureCategory, OptimizationLog
)
from forgeai.core.llm_utils import invoke_with_retry


CRITIC_PROMPT = """You are ForgeAI's Critic. Analyze the evaluation results and prescribe
TARGETED fixes. Do NOT suggest a full rewrite — suggest minimal changes that fix specific failures.

SCORECARD:
- Overall Score: {score:.1%}
- Passed: {passed}/{total}
- Failed: {failed}/{total}

FAILURE BREAKDOWN:
{failure_breakdown}

FAILED CASES:
{failed_cases}

CURRENT SYSTEM PROMPT:
{system_prompt}

CURRENT RETRIEVAL CONFIG:
  chunk_size: {chunk_size}, chunk_overlap: {chunk_overlap}
  top_k: {top_k}, score_threshold: {score_threshold}

CURRENT TOOLS: {tools}

Prescribe targeted fixes as a JSON array of objects:
[
    {{
        "change_type": "prompt_edit|retrieval_param|tool_change",
        "description": "What to change and why",
        "failures_addressed": ["case_id1", "case_id2"],
        "fix_instruction": "Specific instruction for the Agent Generator to apply"
    }}
]

RULES:
1. Each fix must target specific failure cases.
2. For retrieval_miss: consider increasing top_k or adjusting chunk_size.
3. For prompt_defect: prescribe specific prompt additions/modifications.
4. For hallucination: add stronger grounding instructions to the prompt.
5. For wrong_refusal: relax scope constraints for specific topics.
6. For wrong_acceptance: add topics to the refusal list.
7. Keep fixes minimal and targeted — not a full rewrite.

Return ONLY the JSON array, no code fences.
"""


class CriticOptimizer:
    """
    Core Requirement #6: Critic-Optimizer Loop
    Stretch Goal: Budget enforcement with early stopping
    """

    def __init__(self, llm_config: LLMConfig, budget: BudgetConfig):
        self.llm = get_llm(llm_config)
        self.budget = budget

    def analyze_and_prescribe(
        self,
        scorecard: IterationScorecard,
        agent_definition: AgentDefinition
    ) -> List[Dict]:
        """
        Analyze scorecard failures and prescribe targeted fixes.
        Returns a list of fix prescriptions.
        """
        # Format failed cases
        failed_cases = []
        for cs in scorecard.case_scores:
            if cs.score < 0.7:
                failed_cases.append(
                    f"- [{cs.case_id}] ({cs.case_type.value}) Q: {cs.question}\n"
                    f"  Failure: {cs.failure_category.value} — {cs.failure_explanation}\n"
                    f"  Response snippet: {cs.agent_response[:200]}..."
                )

        failure_breakdown = "\n".join(
            f"  {cat}: {count} cases"
            for cat, count in scorecard.failure_breakdown.items()
        )

        messages = [
            SystemMessage(content="You are an expert at diagnosing and fixing AI agent failures."),
            HumanMessage(content=CRITIC_PROMPT.format(
                score=scorecard.score,
                passed=scorecard.passed,
                total=scorecard.total_cases,
                failed=scorecard.failed,
                failure_breakdown=failure_breakdown or "  No failures categorized",
                failed_cases="\n".join(failed_cases) or "  No failed cases",
                system_prompt=agent_definition.system_prompt[:2000],
                chunk_size=agent_definition.retrieval_config.chunk_size,
                chunk_overlap=agent_definition.retrieval_config.chunk_overlap,
                top_k=agent_definition.retrieval_config.top_k,
                score_threshold=agent_definition.retrieval_config.score_threshold,
                tools=agent_definition.tools
            ))
        ]

        response = invoke_with_retry(self.llm, messages)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            fixes = json.loads(content)
            if isinstance(fixes, list):
                return fixes
        except json.JSONDecodeError:
            pass

        return self._fallback_fixes(scorecard)

    def should_continue(
        self,
        current_score: float,
        previous_score: float,
        iteration: int
    ) -> Tuple[bool, str]:
        """
        Determine if optimization should continue.
        Implements budget enforcement (stretch goal).
        """
        # Check iteration limit
        if iteration >= self.budget.max_iterations:
            return False, f"Maximum iterations ({self.budget.max_iterations}) reached"

        # Check budget
        if self.budget.budget_exhausted:
            return False, f"Token budget exhausted ({self.budget.tokens_used}/{self.budget.max_tokens_per_run})"

        # Check early stopping (stretch goal)
        if iteration > 0:
            improvement = current_score - previous_score
            if improvement < self.budget.early_stop_threshold and improvement >= 0:
                return False, (
                    f"Early stopping: improvement ({improvement:.1%}) below "
                    f"threshold ({self.budget.early_stop_threshold:.1%})"
                )

        # Check if score is already very high
        if current_score >= 0.95:
            return False, f"Score already excellent ({current_score:.1%})"

        return True, "Continuing optimization"

    def create_optimization_log(
        self,
        iteration: int,
        fix: Dict,
        score_before: float,
        score_after: float
    ) -> OptimizationLog:
        """Create a log entry for an optimization step."""
        return OptimizationLog(
            iteration=iteration,
            change_type=fix.get("change_type", "prompt_edit"),
            failure_category=fix.get("failure_category", "prompt_defect"),
            diagnosis=fix.get("diagnosis", fix.get("description", "")),
            description=fix.get("description", "No description"),
            reason=fix.get("reason", "Targeted fix prescribed from evaluation failure breakdown"),
            failures_addressed=fix.get("failures_addressed", []),
            score_before=score_before,
            score_after=score_after
        )

    def _fallback_fixes(self, scorecard: IterationScorecard) -> List[Dict]:
        """Generate fallback fixes based on failure breakdown."""
        fixes = []

        if scorecard.failure_breakdown.get("retrieval_miss", 0) > 0:
            fixes.append({
                "change_type": "retrieval_param",
                "description": "Increase top_k to retrieve more context for missed information",
                "failures_addressed": [
                    cs.case_id for cs in scorecard.case_scores
                    if cs.failure_category == FailureCategory.RETRIEVAL_MISS
                ],
                "fix_instruction": "Increase top_k from current value to current+3. Decrease score_threshold by 0.05."
            })

        if scorecard.failure_breakdown.get("hallucination", 0) > 0:
            fixes.append({
                "change_type": "prompt_edit",
                "description": "Add stronger grounding instructions to prevent hallucination",
                "failures_addressed": [
                    cs.case_id for cs in scorecard.case_scores
                    if cs.failure_category == FailureCategory.HALLUCINATION
                ],
                "fix_instruction": (
                    "Add this instruction to the system prompt: "
                    "'CRITICAL: You MUST ONLY state facts that are DIRECTLY present in the "
                    "provided context. If the context does not contain the answer, say "
                    "\"I don't have that information in my documents.\" Never infer, guess, "
                    "or use external knowledge.'"
                )
            })

        if scorecard.failure_breakdown.get("wrong_refusal", 0) > 0:
            fixes.append({
                "change_type": "prompt_edit",
                "description": "Relax scope constraints to prevent wrong refusals",
                "failures_addressed": [
                    cs.case_id for cs in scorecard.case_scores
                    if cs.failure_category == FailureCategory.WRONG_REFUSAL
                ],
                "fix_instruction": (
                    "The agent is refusing questions it should answer. "
                    "Modify the system prompt to be less restrictive about scope. "
                    "The agent should attempt to answer any question that the retrieved "
                    "context can support, even if the topic isn't explicitly listed."
                )
            })

        if scorecard.failure_breakdown.get("wrong_acceptance", 0) > 0:
            fixes.append({
                "change_type": "prompt_edit",
                "description": "Strengthen refusal for out-of-scope questions",
                "failures_addressed": [
                    cs.case_id for cs in scorecard.case_scores
                    if cs.failure_category == FailureCategory.WRONG_ACCEPTANCE
                ],
                "fix_instruction": (
                    "The agent is answering questions it should refuse. "
                    "Add explicit instructions: 'If the question is about topics outside "
                    "your documents, you MUST refuse politely. Do not attempt to answer "
                    "general knowledge questions.'"
                )
            })

        return fixes if fixes else [{
            "change_type": "prompt_edit",
            "description": "General prompt improvement for better accuracy",
            "failures_addressed": [],
            "fix_instruction": "Improve the system prompt to be more precise about when to cite sources and when to refuse."
        }]
