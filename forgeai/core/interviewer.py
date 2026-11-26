"""
Intake Interviewer (Core Requirement #1)
=========================================
Reads the brief, inspects the document folder, asks the requester at most 5
clarifying questions, and writes a structured requirements document.

Also implements the Groundability Guard (Core Requirement #2):
Flags if the brief asks for things the documents cannot support.
"""

import json
from typing import List, Optional

try:
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    from langchain.schema import HumanMessage, SystemMessage

from forgeai.config import LLMConfig, get_llm
from forgeai.models import RequirementsDocument
from forgeai.core.document_processor import load_documents, get_document_summary
from forgeai.core.llm_utils import invoke_with_retry


INTERVIEWER_SYSTEM_PROMPT = """You are ForgeAI's Intake Interviewer. Your job is to analyze a user's
brief (a one-paragraph description of what agent they want) along with their uploaded documents,
and produce a structured requirements document.

You will:
1. Analyze the brief to understand what the user wants.
2. Review the document summaries to understand what knowledge is available.
3. Generate at most 5 clarifying questions to ask the user.
4. CRITICALLY: Check for GROUNDABILITY — if the brief asks for capabilities that the documents
   CANNOT support, you MUST flag this. Do NOT let an agent be built that will hallucinate.

Your questions should focus on:
- Ambiguities in the brief
- Tone and formality preferences
- Edge cases and boundaries
- Topics that should be explicitly refused

Output your questions as a JSON list of strings.
"""

REQUIREMENTS_GENERATION_PROMPT = """Based on the brief, document analysis, and user clarifications,
produce a structured requirements document as JSON.

Brief: {brief}

Document Summary:
{doc_summary}

User Clarifications:
{clarifications}

GROUNDABILITY CHECK:
Carefully compare what the brief asks for against what the documents actually contain.
If there are gaps — topics the brief mentions but documents don't cover — list them as
groundability_warnings. These are CRITICAL: an agent that claims to know things not in
its documents is worse than one that honestly says "I don't have that information."

Available tools in the registry: {available_tools}
Only select tools that the brief ACTUALLY needs. An HR policy agent does NOT need a weather tool.
A procurement agent might need csv_lookup but not a calculator.

Produce a JSON object with these exact fields:
{{
    "scope": "what the agent does",
    "audience": "who uses it",
    "tone": "communication style",
    "must_answer_topics": ["topic1", "topic2"],
    "must_refuse_topics": ["topic1", "topic2"],
    "required_capabilities": ["capability1", "capability2"],
    "document_coverage": ["filename: summary of covered topics"],
    "document_summary": "what the docs contain",
    "groundability_warnings": ["warning1 if any"],
    "unsupported_requirements": ["unsupported capability or topic if any"],
    "tools_needed": ["tool_name1"],
    "clarifications": [{{"question": "q", "answer": "a"}}]
}}

Return ONLY the JSON, no markdown code fences or extra text.
"""


class IntakeInterviewer:
    """
    Core Requirement #1: Intake Interviewer
    Core Requirement #2: Groundability Guard
    """

    def __init__(self, llm_config: LLMConfig, available_tools: List[str]):
        self.llm = get_llm(llm_config)
        self.available_tools = available_tools

    def generate_questions(self, brief: str, doc_summary: str) -> List[str]:
        """Generate clarifying questions based on the brief and documents."""
        messages = [
            SystemMessage(content=INTERVIEWER_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"Brief: {brief}\n\n"
                f"Document Summary:\n{doc_summary}\n\n"
                f"Available Tools: {', '.join(self.available_tools)}\n\n"
                "Generate at most 5 clarifying questions as a JSON list of strings. "
                "Return ONLY the JSON array, no code fences."
            ))
        ]
        response = invoke_with_retry(self.llm, messages)
        try:
            # Try to parse as JSON
            content = response.content.strip()
            # Remove code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            questions = json.loads(content)
            if isinstance(questions, list):
                return questions[:5]
        except (json.JSONDecodeError, IndexError):
            # Fallback: split by newlines
            lines = [l.strip().lstrip("0123456789.-) ") for l in response.content.strip().split("\n") if l.strip()]
            return lines[:5]
        return ["What is the primary use case for this agent?"]

    def build_requirements(
        self,
        brief: str,
        doc_folder: str,
        clarifications: Optional[List[dict]] = None,
        auto_mode: bool = False
    ) -> RequirementsDocument:
        """
        Build a complete requirements document.
        
        Args:
            brief: One-paragraph description of desired agent
            doc_folder: Path to folder containing documents
            clarifications: Pre-provided Q&A (for auto mode)
            auto_mode: If True, auto-generate answers to questions
        """
        # Load and analyze documents
        documents = load_documents(doc_folder)
        doc_summary = get_document_summary(documents)

        if clarifications is None:
            # Generate questions
            questions = self.generate_questions(brief, doc_summary)

            if auto_mode:
                # Auto-answer questions using the LLM
                clarifications = self._auto_answer_questions(brief, doc_summary, questions)
            else:
                # Interactive mode - ask user
                clarifications = self._interactive_questions(questions)

        # Generate requirements document
        clarifications_text = "\n".join(
            f"Q: {c.get('question', 'N/A')}\nA: {c.get('answer', 'N/A')}"
            for c in clarifications
        )

        messages = [
            SystemMessage(content="You are a requirements analyst. Produce structured JSON."),
            HumanMessage(content=REQUIREMENTS_GENERATION_PROMPT.format(
                brief=brief,
                doc_summary=doc_summary,
                clarifications=clarifications_text,
                available_tools=", ".join(self.available_tools)
            ))
        ]

        response = invoke_with_retry(self.llm, messages)
        content = response.content.strip()

        # Parse JSON response
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            data = json.loads(content)
            data["clarifications"] = clarifications
            req = RequirementsDocument(**data)
        except (json.JSONDecodeError, Exception):
            # Fallback: create a basic requirements doc
            req = RequirementsDocument(
                scope=brief,
                audience="General users",
                tone="Professional and helpful",
                must_answer_topics=["Topics covered in provided documents"],
                must_refuse_topics=["Topics not in documents", "Personal opinions"],
                required_capabilities=[brief],
                document_coverage=[doc_summary[:200]],
                document_summary=doc_summary,
                groundability_warnings=[],
                unsupported_requirements=[],
                tools_needed=[],
                clarifications=clarifications or []
            )

        # Groundability Guard enforcement: ensure flagged unsupported items are in must_refuse_topics
        for item in req.groundability_warnings + req.unsupported_requirements:
            if item and item not in req.must_refuse_topics:
                req.must_refuse_topics.append(item)
        if not req.unsupported_requirements and req.groundability_warnings:
            req.unsupported_requirements = list(req.groundability_warnings)
        req.tools_needed = [t for t in req.tools_needed if t in self.available_tools]
        return req

    def _auto_answer_questions(
        self, brief: str, doc_summary: str, questions: List[str]
    ) -> List[dict]:
        """Auto-generate answers to clarifying questions (for unattended runs)."""
        messages = [
            SystemMessage(content=(
                "You are simulating a requester who wrote this brief. "
                "Answer the clarifying questions based on the brief and common sense. "
                "Be specific and practical."
            )),
            HumanMessage(content=(
                f"Brief: {brief}\n\n"
                f"Available Documents:\n{doc_summary}\n\n"
                f"Questions:\n" +
                "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions)) +
                "\n\nAnswer each question concisely. Format as JSON list of objects with "
                "'question' and 'answer' keys. Return ONLY the JSON array."
            ))
        ]
        response = invoke_with_retry(self.llm, messages)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return [{"question": q, "answer": "Use best judgment based on the brief."} for q in questions]

    def _interactive_questions(self, questions: List[str]) -> List[dict]:
        """Ask questions interactively via CLI."""
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        clarifications = []

        console.print(Panel(
            "[bold cyan]ForgeAI Intake Interview[/bold cyan]\n"
            "Please answer the following clarifying questions:",
            border_style="cyan"
        ))

        for i, question in enumerate(questions, 1):
            console.print(f"\n[bold yellow]Q{i}:[/bold yellow] {question}")
            answer = input("→ Your answer: ").strip()
            if not answer:
                answer = "No specific preference, use best judgment."
            clarifications.append({"question": question, "answer": answer})

        return clarifications
