"""
Judge (Core Requirement #5)
============================
Automated scoring per test case: grounded? correct against expected facts?
refused when it should? Uses LLM-as-judge with defenses against known biases
(position bias, self-preference, verbosity bias) plus deterministic checks.
"""

import json
import re
from typing import List, Optional

try:
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    from langchain.schema import HumanMessage, SystemMessage

from forgeai.config import LLMConfig, get_llm
from forgeai.models import (
    EvalCase, EvalCaseType, CaseScore, FailureCategory, IterationScorecard
)


JUDGE_PROMPT = """You are ForgeAI's impartial Judge. Score this agent response against the test case.

TEST CASE:
- Question: {question}
- Type: {case_type}
- Expected Facts: {expected_facts}
- Should Refuse: {should_refuse}
- Source Document: {source_doc}

AGENT RESPONSE:
{response}

RETRIEVED CONTEXT:
{context}

Score the response on these criteria and return a JSON object:

{{
    "is_grounded": true/false,  // Is the answer supported by the retrieved context?
    "is_correct": true/false,   // Does it contain the expected facts? (for answerable questions)
    "correctly_refused": true/false,  // Did it properly refuse if it should have?
    "score": 0.0-1.0,          // Overall score
    "failure_category": "none|retrieval_miss|prompt_defect|hallucination|wrong_refusal|wrong_acceptance|incomplete",
    "failure_explanation": "Brief explanation if score < 1.0"
}}

JUDGING RULES (bias defenses):
1. POSITION BIAS defense: Judge the content, not whether the answer appears first or last.
2. SELF-PREFERENCE defense: You have no preference for any style. Focus on factual accuracy.
3. VERBOSITY BIAS defense: A longer answer is NOT automatically better. A concise correct answer
   beats a verbose partially-correct one.
4. For ANSWERABLE questions: Check if ALL expected facts are present, not just some.
5. For OUT_OF_SCOPE questions: The agent MUST refuse. Any attempt to answer is wrong.
6. For EDGE CASES: Judge reasonableness — the agent should handle gracefully.

FAILURE CATEGORIES:
- retrieval_miss: The relevant information was not in the retrieved context
- prompt_defect: The context had the right info but the agent misused it
- hallucination: The agent stated facts NOT in the retrieved context
- wrong_refusal: The agent refused a question it should have answered
- wrong_acceptance: The agent answered a question it should have refused
- incomplete: The answer is partially correct but missing key facts
- none: No failure

Return ONLY the JSON object, no code fences.
"""


class Judge:
    """
    Core Requirement #5: Automated Judge
    Combines LLM-as-judge with deterministic checks for reliability.
    """

    def __init__(self, llm_config: LLMConfig):
        self.llm = get_llm(llm_config)

    def score_case(
        self,
        case: EvalCase,
        agent_response: str,
        retrieved_chunks: List[str]
    ) -> CaseScore:
        """Score a single evaluation case."""
        # First: deterministic checks
        deterministic_score = self._deterministic_checks(case, agent_response, retrieved_chunks)

        # Then: LLM judge for nuanced assessment
        llm_score = self._llm_judge(case, agent_response, retrieved_chunks)

        # Combine: deterministic checks can OVERRIDE LLM if they detect clear issues
        final_score = self._combine_scores(deterministic_score, llm_score, case)

        return final_score

    def score_all(
        self,
        cases: List[EvalCase],
        responses: List[str],
        contexts: List[List[str]],
        iteration: int
    ) -> IterationScorecard:
        """Score all evaluation cases and produce a scorecard."""
        case_scores = []
        for case, response, context in zip(cases, responses, contexts):
            score = self.score_case(case, response, context)
            case_scores.append(score)

        # Calculate aggregate metrics
        total = len(case_scores)
        passed = sum(1 for s in case_scores if s.score >= 0.7)
        failed = total - passed
        avg_score = sum(s.score for s in case_scores) / total if total > 0 else 0.0

        # Failure breakdown
        failure_breakdown = {}
        for s in case_scores:
            if s.failure_category != FailureCategory.NONE:
                cat = s.failure_category.value
                failure_breakdown[cat] = failure_breakdown.get(cat, 0) + 1

        return IterationScorecard(
            iteration=iteration,
            total_cases=total,
            passed=passed,
            failed=failed,
            score=round(avg_score, 4),
            case_scores=case_scores,
            failure_breakdown=failure_breakdown,
        )

    def _deterministic_checks(
        self,
        case: EvalCase,
        response: str,
        retrieved_chunks: List[str]
    ) -> CaseScore:
        """Run deterministic (non-LLM) checks for reliable baseline scoring."""
        response_lower = response.lower().strip()
        context_text = " ".join(retrieved_chunks).lower()

        is_refusal = any(phrase in response_lower for phrase in [
            "i can't", "i cannot", "i don't have", "outside my scope",
            "i'm not able", "not within my", "i am not able",
            "beyond my scope", "i'm unable", "unable to answer",
            "don't have information", "not in my documents",
            "outside the scope", "i can only answer"
        ])

        # Check for out-of-scope handling
        if case.should_refuse:
            if is_refusal:
                return CaseScore(
                    case_id=case.id,
                    question=case.question,
                    case_type=case.case_type,
                    agent_response=response,
                    is_grounded=True,
                    is_correct=True,
                    correctly_refused=True,
                    score=1.0,
                    failure_category=FailureCategory.NONE,
                    retrieved_chunks=retrieved_chunks
                )
            else:
                return CaseScore(
                    case_id=case.id,
                    question=case.question,
                    case_type=case.case_type,
                    agent_response=response,
                    is_grounded=False,
                    is_correct=False,
                    correctly_refused=False,
                    score=0.0,
                    failure_category=FailureCategory.WRONG_ACCEPTANCE,
                    failure_explanation="Agent answered an out-of-scope question it should have refused",
                    retrieved_chunks=retrieved_chunks
                )

        # For answerable questions
        if case.case_type == EvalCaseType.ANSWERABLE and not case.should_refuse:
            if is_refusal:
                return CaseScore(
                    case_id=case.id,
                    question=case.question,
                    case_type=case.case_type,
                    agent_response=response,
                    is_grounded=False,
                    is_correct=False,
                    correctly_refused=False,
                    score=0.0,
                    failure_category=FailureCategory.WRONG_REFUSAL,
                    failure_explanation="Agent refused an answerable question",
                    retrieved_chunks=retrieved_chunks
                )

            # Check if expected facts are present
            facts_found = 0
            for fact in case.expected_answer_facts:
                fact_words = set(fact.lower().split())
                # Fuzzy match: at least 60% of fact words should appear
                words_in_response = sum(1 for w in fact_words if w in response_lower)
                if words_in_response >= max(1, len(fact_words) * 0.6):
                    facts_found += 1

            if case.expected_answer_facts:
                fact_ratio = facts_found / len(case.expected_answer_facts)
            else:
                fact_ratio = 0.5  # No expected facts to check

            # Check groundedness
            is_grounded = len(retrieved_chunks) > 0 and len(response.strip()) > 10

            return CaseScore(
                case_id=case.id,
                question=case.question,
                case_type=case.case_type,
                agent_response=response,
                is_grounded=is_grounded,
                is_correct=fact_ratio >= 0.7,
                correctly_refused=True,
                score=round(fact_ratio * 0.7 + (0.3 if is_grounded else 0.0), 4),
                failure_category=(
                    FailureCategory.INCOMPLETE if fact_ratio < 1.0 and fact_ratio > 0
                    else FailureCategory.RETRIEVAL_MISS if fact_ratio == 0
                    else FailureCategory.NONE
                ),
                failure_explanation=(
                    f"Found {facts_found}/{len(case.expected_answer_facts)} expected facts"
                    if fact_ratio < 1.0 else ""
                ),
                retrieved_chunks=retrieved_chunks
            )

        # Default for edge cases
        return CaseScore(
            case_id=case.id,
            question=case.question,
            case_type=case.case_type,
            agent_response=response,
            is_grounded=len(retrieved_chunks) > 0,
            is_correct=len(response.strip()) > 10,
            correctly_refused=True,
            score=0.5,  # Placeholder for LLM judge
            failure_category=FailureCategory.NONE,
            retrieved_chunks=retrieved_chunks
        )

    def _llm_judge(
        self,
        case: EvalCase,
        response: str,
        retrieved_chunks: List[str]
    ) -> Optional[CaseScore]:
        """Use LLM as judge for nuanced assessment."""
        try:
            context = "\n---\n".join(retrieved_chunks[:5]) if retrieved_chunks else "(No context retrieved)"

            messages = [
                SystemMessage(content="You are an impartial AI response judge. Be strict and fair."),
                HumanMessage(content=JUDGE_PROMPT.format(
                    question=case.question,
                    case_type=case.case_type.value,
                    expected_facts=json.dumps(case.expected_answer_facts),
                    should_refuse=case.should_refuse,
                    source_doc=case.source_document or "N/A",
                    response=response,
                    context=context
                ))
            ]

            result = self.llm.invoke(messages)
            content = result.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            data = json.loads(content)

            failure_cat = data.get("failure_category", "none")
            try:
                failure_category = FailureCategory(failure_cat)
            except ValueError:
                failure_category = FailureCategory.NONE

            return CaseScore(
                case_id=case.id,
                question=case.question,
                case_type=case.case_type,
                agent_response=response,
                is_grounded=data.get("is_grounded", False),
                is_correct=data.get("is_correct", False),
                correctly_refused=data.get("correctly_refused", True),
                score=min(1.0, max(0.0, float(data.get("score", 0.5)))),
                failure_category=failure_category,
                failure_explanation=data.get("failure_explanation", ""),
                retrieved_chunks=retrieved_chunks
            )
        except Exception:
            return None

    def _combine_scores(
        self,
        deterministic: CaseScore,
        llm_score: Optional[CaseScore],
        case: EvalCase
    ) -> CaseScore:
        """
        Combine deterministic and LLM scores.
        Deterministic checks OVERRIDE for clear-cut cases.
        """
        if llm_score is None:
            return deterministic

        # For refusal cases, deterministic check is authoritative
        if case.should_refuse:
            return deterministic

        # For wrong refusals, deterministic check is authoritative
        if deterministic.failure_category == FailureCategory.WRONG_REFUSAL:
            return deterministic

        # Otherwise, average the scores with slight weight to deterministic
        combined_score = round(deterministic.score * 0.4 + llm_score.score * 0.6, 4)

        # Use LLM's failure analysis if it found something specific
        failure_category = llm_score.failure_category
        failure_explanation = llm_score.failure_explanation
        if deterministic.failure_category != FailureCategory.NONE and llm_score.failure_category == FailureCategory.NONE:
            failure_category = deterministic.failure_category
            failure_explanation = deterministic.failure_explanation

        return CaseScore(
            case_id=case.id,
            question=case.question,
            case_type=case.case_type,
            agent_response=deterministic.agent_response,
            is_grounded=deterministic.is_grounded and llm_score.is_grounded,
            is_correct=deterministic.is_correct or llm_score.is_correct,
            correctly_refused=deterministic.correctly_refused and llm_score.correctly_refused,
            score=combined_score,
            failure_category=failure_category,
            failure_explanation=failure_explanation,
            retrieved_chunks=deterministic.retrieved_chunks
        )
