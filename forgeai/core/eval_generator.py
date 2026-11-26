"""
Eval Generator (Core Requirement #4)
=====================================
Auto-creates a test set from the documents themselves: answerable questions
(with grounding), out-of-scope questions, and edge cases.
"""

import json
from typing import List

try:
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    from langchain.schema import HumanMessage, SystemMessage

from forgeai.config import LLMConfig, get_llm
from forgeai.models import (
    RequirementsDocument, EvalCase, EvalSet, EvalCaseType
)
from forgeai.core.llm_utils import invoke_with_retry


EVAL_GENERATION_PROMPT = """You are ForgeAI's Evaluation Set Generator. Your job is to create a
comprehensive test set for evaluating an AI agent.

Agent Requirements:
{requirements}

Document Content Samples (use these to create GROUNDED questions):
{doc_samples}

Generate EXACTLY {num_cases} test cases as a JSON array. Each case must have:
{{
    "id": "case_XX",
    "question": "the test question",
    "case_type": "answerable|out_of_scope|edge_case|multi_document",
    "expected_answer_facts": ["fact1", "fact2"],  // key facts for answerable questions
    "source_document": "document_name.pdf",  // which doc has the answer
    "should_refuse": false  // true for out_of_scope questions
}}

DISTRIBUTION REQUIREMENTS:
- At least 10 answerable questions (with specific expected facts from the documents)
- At least 4 out-of-scope questions the agent MUST refuse
- At least 3 edge cases (ambiguous phrasing, partial matches, trick questions)
- At least 3 multi-document questions (answers spanning 2+ documents)

QUALITY RULES:
1. Answerable questions MUST have verifiable facts from the actual document content
2. Out-of-scope questions should be plausible but clearly outside the agent's domain
3. Edge cases should test boundary conditions (e.g., asking about something adjacent to scope)
4. Multi-document cases should require combining information from different sources
5. Expected facts must be SPECIFIC and VERIFIABLE, not vague

Return ONLY the JSON array, no markdown code fences or extra text.
"""


class EvalGenerator:
    """
    Core Requirement #4: Eval Generator
    Generates test sets from documents, not hand-written.
    """

    def __init__(self, llm_config: LLMConfig):
        self.llm = get_llm(llm_config)

    def generate(
        self,
        requirements: RequirementsDocument,
        document_samples: List[str],
        num_cases: int = 24
    ) -> EvalSet:
        """Generate an evaluation test set from documents and requirements."""
        # Prepare document samples (truncated for prompt)
        doc_samples_text = "\n\n---\n\n".join(
            sample[:800] for sample in document_samples[:10]
        )

        prompt = EVAL_GENERATION_PROMPT.format(
            requirements=json.dumps(requirements.model_dump(), indent=2),
            doc_samples=doc_samples_text,
            num_cases=num_cases
        )

        messages = [
            SystemMessage(content="You are a QA engineer creating thorough test cases."),
            HumanMessage(content=prompt)
        ]

        response = invoke_with_retry(self.llm, messages)
        content = response.content.strip()

        # Clean response
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            cases_data = json.loads(content)
            cases = []
            for cd in cases_data:
                try:
                    raw_type = cd.get("case_type") or cd.get("category") or "answerable"
                    if raw_type == "refusal":
                        raw_type = "out_of_scope"
                    elif raw_type == "ambiguous":
                        raw_type = "edge_case"
                    case_type = EvalCaseType(raw_type)
                    should_refuse = bool(cd.get("should_refuse", case_type == EvalCaseType.OUT_OF_SCOPE))
                    expected_sources = cd.get("expected_sources") or (
                        [cd["source_document"]] if cd.get("source_document") else []
                    )
                    cases.append(EvalCase(
                        id=cd.get("id", f"case_{len(cases)+1:02d}"),
                        question=cd["question"],
                        case_type=case_type,
                        expected_behavior=cd.get("expected_behavior", "refuse" if should_refuse else "answer"),
                        expected_answer_facts=cd.get("expected_answer_facts") or cd.get("expected_facts", []),
                        source_document=cd.get("source_document") or (expected_sources[0] if expected_sources else None),
                        expected_sources=expected_sources,
                        should_refuse=should_refuse,
                        grading_notes=cd.get("grading_notes", "")
                    ))
                except Exception:
                    continue

            # Ensure minimum cases
            if len(cases) < 20:
                cases = self._pad_eval_set(cases, requirements, num_cases)

            return EvalSet(
                cases=cases,
                generation_prompt=prompt,
            )
        except json.JSONDecodeError:
            # Fallback: generate a minimal set
            return self._generate_fallback_eval_set(requirements)

    def _pad_eval_set(
        self,
        existing_cases: List[EvalCase],
        requirements: RequirementsDocument,
        target: int
    ) -> List[EvalCase]:
        """Pad eval set if we didn't get enough cases."""
        cases = list(existing_cases)

        # Add domain-independent out-of-scope cases (respecting selected tools)
        oos_topics = [
            "Can you write me a poem about outer space?",
            "What is the capital of France?",
            "Can you diagnose my medical symptoms and prescribe medication?",
            "Tell me a joke about software engineers.",
        ]
        if "weather_api" not in requirements.tools_needed:
            oos_topics.insert(0, "What is the weather forecast today?")
        for i, q in enumerate(oos_topics):
            if len(cases) >= target:
                break
            cases.append(EvalCase(
                id=f"case_pad_oos_{i+1:02d}",
                question=q,
                case_type=EvalCaseType.OUT_OF_SCOPE,
                expected_behavior="refuse",
                should_refuse=True,
                expected_answer_facts=[],
                grading_notes="Out-of-scope query; agent must refuse."
            ))

        return cases

    def _generate_fallback_eval_set(
        self,
        requirements: RequirementsDocument
    ) -> EvalSet:
        """Generate a minimal fallback eval set."""
        cases = []

        # Basic answerable cases from topics
        for i, topic in enumerate(requirements.must_answer_topics[:5]):
            cases.append(EvalCase(
                id=f"case_fallback_{i+1:02d}",
                question=f"Tell me about {topic}",
                case_type=EvalCaseType.ANSWERABLE,
                expected_answer_facts=[topic],
                should_refuse=False
            ))

        # Basic out-of-scope
        for i, topic in enumerate(requirements.must_refuse_topics[:5]):
            cases.append(EvalCase(
                id=f"case_fallback_oos_{i+1:02d}",
                question=f"What about {topic}?",
                case_type=EvalCaseType.OUT_OF_SCOPE,
                should_refuse=True,
                expected_answer_facts=[]
            ))

        # Edge cases
        cases.extend([
            EvalCase(
                id="case_fallback_edge_01",
                question="?",
                case_type=EvalCaseType.EDGE_CASE,
                should_refuse=False,
                expected_answer_facts=[]
            ),
            EvalCase(
                id="case_fallback_edge_02",
                question="Tell me everything",
                case_type=EvalCaseType.EDGE_CASE,
                should_refuse=False,
                expected_answer_facts=[]
            ),
        ])

        return EvalSet(
            cases=cases,
            generation_prompt="FALLBACK: Auto-generated from requirements topics",
        )
