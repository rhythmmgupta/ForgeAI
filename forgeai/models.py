"""
Data Models for ForgeAI
Pydantic models defining the structured data flowing through the pipeline.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime


# ─── Requirements Models ────────────────────────────────────────────────────

class RequirementsDocument(BaseModel):
    """Structured requirements produced by the Intake Interviewer."""
    scope: str = Field(description="What the agent is meant to do")
    audience: str = Field(description="Who will use this agent")
    tone: str = Field(description="Communication style (formal, friendly, technical, etc.)")
    must_answer_topics: List[str] = Field(description="Topics the agent MUST be able to answer")
    must_refuse_topics: List[str] = Field(description="Topics the agent MUST refuse to answer")
    document_summary: str = Field(description="Summary of what the uploaded documents contain")
    groundability_warnings: List[str] = Field(
        default_factory=list,
        description="Warnings about brief requests not supported by documents"
    )
    tools_needed: List[str] = Field(
        default_factory=list,
        description="Tool names from registry that this agent needs"
    )
    clarifications: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Q&A from the clarification interview"
    )


# ─── Agent Definition Models ────────────────────────────────────────────────

class RetrievalConfig(BaseModel):
    """Configuration for the RAG retrieval pipeline."""
    chunk_size: int = Field(default=500, description="Characters per text chunk")
    chunk_overlap: int = Field(default=100, description="Overlap between chunks")
    top_k: int = Field(default=5, description="Number of chunks to retrieve")
    score_threshold: float = Field(default=0.3, description="Minimum similarity score")


class OutputContract(BaseModel):
    """Defines the expected output format of the agent."""
    format: str = Field(default="markdown", description="Output format: markdown, json, plain")
    max_length: int = Field(default=500, description="Maximum response length in words")
    must_cite_sources: bool = Field(default=True, description="Whether to cite document sources")
    refusal_template: str = Field(
        default="I can only answer questions related to {scope}. This question is outside my scope.",
        description="Template for refusing out-of-scope questions"
    )


class AgentDefinition(BaseModel):
    """Complete declarative agent definition produced by the Agent Generator."""
    name: str = Field(description="Agent name")
    system_prompt: str = Field(description="The full system prompt for the agent")
    retrieval_config: RetrievalConfig = Field(default_factory=RetrievalConfig)
    tools: List[str] = Field(default_factory=list, description="Tool names from registry")
    output_contract: OutputContract = Field(default_factory=OutputContract)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    iteration: int = Field(default=0, description="Which optimization iteration produced this")


# ─── Evaluation Models ──────────────────────────────────────────────────────

class EvalCaseType(str, Enum):
    ANSWERABLE = "answerable"
    OUT_OF_SCOPE = "out_of_scope"
    EDGE_CASE = "edge_case"
    MULTI_DOCUMENT = "multi_document"


class EvalCase(BaseModel):
    """A single evaluation test case."""
    id: str = Field(description="Unique case identifier")
    question: str = Field(description="The test question")
    case_type: EvalCaseType = Field(description="Type of test case")
    expected_answer_facts: List[str] = Field(
        default_factory=list,
        description="Key facts that must appear in the answer (for answerable questions)"
    )
    source_document: Optional[str] = Field(
        default=None,
        description="Which document(s) contain the answer"
    )
    should_refuse: bool = Field(
        default=False,
        description="Whether the agent should refuse this question"
    )


class EvalSet(BaseModel):
    """Complete evaluation test set."""
    cases: List[EvalCase] = Field(description="All test cases")
    generation_prompt: str = Field(description="The prompt used to generate these cases")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ─── Scoring Models ─────────────────────────────────────────────────────────

class FailureCategory(str, Enum):
    RETRIEVAL_MISS = "retrieval_miss"
    PROMPT_DEFECT = "prompt_defect"
    HALLUCINATION = "hallucination"
    WRONG_REFUSAL = "wrong_refusal"
    WRONG_ACCEPTANCE = "wrong_acceptance"
    INCOMPLETE = "incomplete"
    NONE = "none"  # No failure


class CaseScore(BaseModel):
    """Score for a single evaluation case."""
    case_id: str
    question: str
    case_type: EvalCaseType
    agent_response: str = ""
    is_grounded: bool = False
    is_correct: bool = False
    correctly_refused: bool = True  # True if refusal behavior is correct
    score: float = Field(ge=0.0, le=1.0, description="Overall score 0-1")
    failure_category: FailureCategory = FailureCategory.NONE
    failure_explanation: str = ""
    retrieved_chunks: List[str] = Field(default_factory=list)


class IterationScorecard(BaseModel):
    """Scorecard for one optimization iteration."""
    iteration: int
    total_cases: int
    passed: int
    failed: int
    score: float = Field(ge=0.0, le=1.0)
    case_scores: List[CaseScore] = Field(default_factory=list)
    failure_breakdown: Dict[str, int] = Field(default_factory=dict)
    changes_made: List[str] = Field(default_factory=list)
    tokens_used: int = 0


class OptimizationLog(BaseModel):
    """Log entry for what changed between iterations."""
    iteration: int
    change_type: str  # "prompt_edit", "retrieval_param", "tool_change"
    description: str
    failures_addressed: List[str]  # Case IDs
    score_before: float
    score_after: float


# ─── Final Report ────────────────────────────────────────────────────────────

class ForgeAIReport(BaseModel):
    """Final honest report from the ForgeAI factory."""
    agent_definition: AgentDefinition
    requirements: RequirementsDocument
    eval_set: EvalSet
    scorecards: List[IterationScorecard] = Field(default_factory=list)
    optimization_logs: List[OptimizationLog] = Field(default_factory=list)
    final_score: float = 0.0
    known_failures: List[str] = Field(
        default_factory=list,
        description="Honest account of what still fails and why"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Suggestions for further improvement"
    )
    total_tokens_used: int = 0
    total_iterations: int = 0
    prompt_tournament_results: Optional[Dict[str, Any]] = None
