"""
Agent Generator (Core Requirement #3)
======================================
From requirements plus documents, produces a complete declarative agent definition:
system prompt, chunking/retrieval parameters, tool selection, and output contract.

Also implements Prompt Tournament (Stretch Goal):
Generates multiple candidate system prompts and picks the best one.
"""

import json
from typing import List, Optional, Dict, Any

try:
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    from langchain.schema import HumanMessage, SystemMessage

from forgeai.config import LLMConfig, get_llm
from forgeai.models import (
    RequirementsDocument, AgentDefinition, RetrievalConfig, OutputContract
)


AGENT_GENERATOR_PROMPT = """You are ForgeAI's Agent Generator. Given a structured requirements
document, you must produce a COMPLETE declarative agent definition.

Requirements:
{requirements}

Your output must be a JSON object with these fields:
{{
    "name": "A descriptive agent name",
    "system_prompt": "The COMPLETE system prompt for this agent. This is the most critical part.
        It must:
        - Define the agent's role and scope clearly
        - Specify what topics it can answer (from the must_answer_topics)
        - Explicitly instruct it to REFUSE topics in must_refuse_topics
        - Set the tone as specified
        - Instruct it to ALWAYS cite source documents
        - Instruct it to say 'I don't have information about that in my documents' rather than
          making up answers
        - Include the groundability warnings as internal guardrails
        - Be specific and detailed, NOT vague",
    "retrieval_config": {{
        "chunk_size": 500,
        "chunk_overlap": 100,
        "top_k": 5,
        "score_threshold": 0.3
    }},
    "tools": ["only_tools_the_brief_actually_needs"],
    "output_contract": {{
        "format": "markdown",
        "max_length": 500,
        "must_cite_sources": true,
        "refusal_template": "A specific refusal message for this agent"
    }}
}}

CRITICAL RULES:
1. The system prompt must be DETAILED and SPECIFIC to this use case - not generic.
2. Only include tools that the brief genuinely needs. Including unnecessary tools is a DEFECT.
3. The refusal template must match the agent's scope.
4. If there are groundability warnings, the system prompt must include explicit instructions
   to NOT answer questions about those topics.

Return ONLY the JSON object, no markdown code fences.
"""

PROMPT_VARIANT_INSTRUCTION = """Generate a DIFFERENT variant of the system prompt for the same agent.
This variant should take a {approach} approach:
- Variant 1 (structured): Uses numbered lists, clear sections, explicit rules
- Variant 2 (conversational): More natural, flowing instructions
- Variant 3 (minimal): Concise, only essential instructions

Keep all the same requirements and guardrails, but vary the STYLE and STRUCTURE.
The core rules (what to answer, what to refuse, citation requirements) must remain identical.
"""


class AgentGenerator:
    """
    Core Requirement #3: Agent Generator
    Stretch Goal: Prompt Tournament
    """

    def __init__(self, llm_config: LLMConfig, available_tools: List[str]):
        self.llm = get_llm(llm_config)
        self.available_tools = available_tools

    def generate(
        self,
        requirements: RequirementsDocument,
        iteration: int = 0
    ) -> AgentDefinition:
        """Generate a complete agent definition from requirements."""
        req_text = json.dumps(requirements.model_dump(), indent=2)

        messages = [
            SystemMessage(content="You are an expert AI agent designer."),
            HumanMessage(content=AGENT_GENERATOR_PROMPT.format(requirements=req_text))
        ]

        response = self.llm.invoke(messages)
        content = response.content.strip()

        # Clean response
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            data = json.loads(content)
            # Validate tools against available tools
            data["tools"] = [t for t in data.get("tools", []) if t in self.available_tools]
            # Only keep tools the requirements say are needed
            needed = set(requirements.tools_needed)
            data["tools"] = [t for t in data["tools"] if t in needed]
            data["iteration"] = iteration

            # Parse nested objects
            if isinstance(data.get("retrieval_config"), dict):
                data["retrieval_config"] = RetrievalConfig(**data["retrieval_config"])
            if isinstance(data.get("output_contract"), dict):
                data["output_contract"] = OutputContract(**data["output_contract"])

            return AgentDefinition(**data)
        except Exception as e:
            # Fallback: create a basic definition
            return self._create_fallback_definition(requirements, iteration)

    def generate_tournament(
        self,
        requirements: RequirementsDocument
    ) -> List[AgentDefinition]:
        """
        Stretch Goal: Prompt Tournament
        Generate multiple candidate agent definitions with different prompt styles.
        """
        candidates = []

        # Generate base definition
        base = self.generate(requirements, iteration=0)
        candidates.append(base)

        # Generate variants
        approaches = ["structured", "conversational", "minimal"]
        for approach in approaches:
            variant = self._generate_variant(requirements, base, approach)
            if variant:
                candidates.append(variant)

        return candidates

    def _generate_variant(
        self,
        requirements: RequirementsDocument,
        base: AgentDefinition,
        approach: str
    ) -> Optional[AgentDefinition]:
        """Generate a prompt variant with a different style."""
        try:
            messages = [
                SystemMessage(content="You are an expert at writing AI system prompts."),
                HumanMessage(content=(
                    f"Here is the base system prompt for an agent:\n\n"
                    f"{base.system_prompt}\n\n"
                    f"Requirements:\n{json.dumps(requirements.model_dump(), indent=2)}\n\n"
                    f"{PROMPT_VARIANT_INSTRUCTION.format(approach=approach)}\n\n"
                    f"Return ONLY the new system prompt text, nothing else."
                ))
            ]
            response = self.llm.invoke(messages)
            variant_prompt = response.content.strip()
            if variant_prompt.startswith("```"):
                variant_prompt = variant_prompt.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            return AgentDefinition(
                name=f"{base.name} ({approach})",
                system_prompt=variant_prompt,
                retrieval_config=base.retrieval_config,
                tools=base.tools,
                output_contract=base.output_contract,
                iteration=0
            )
        except Exception:
            return None

    def apply_fix(
        self,
        current_definition: AgentDefinition,
        fix_instruction: str,
        iteration: int
    ) -> AgentDefinition:
        """
        Apply a targeted fix to the agent definition.
        Used by the Critic-Optimizer loop (Requirement #6).
        """
        messages = [
            SystemMessage(content=(
                "You are an expert at fixing AI agent system prompts. "
                "Apply the specified fix WITHOUT rewriting the entire prompt. "
                "Make minimal, targeted changes."
            )),
            HumanMessage(content=(
                f"Current system prompt:\n{current_definition.system_prompt}\n\n"
                f"Current retrieval config:\n"
                f"  chunk_size: {current_definition.retrieval_config.chunk_size}\n"
                f"  chunk_overlap: {current_definition.retrieval_config.chunk_overlap}\n"
                f"  top_k: {current_definition.retrieval_config.top_k}\n"
                f"  score_threshold: {current_definition.retrieval_config.score_threshold}\n\n"
                f"Current tools: {current_definition.tools}\n\n"
                f"Fix to apply:\n{fix_instruction}\n\n"
                f"Return a JSON object with the MODIFIED fields only. "
                f"Include 'system_prompt' if you changed the prompt. "
                f"Include 'retrieval_config' dict if you changed retrieval params. "
                f"Include 'tools' list if you changed tools. "
                f"Return ONLY JSON, no code fences."
            ))
        ]

        response = self.llm.invoke(messages)
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            fixes = json.loads(content)
            # Apply fixes to a copy
            new_def = current_definition.model_copy(deep=True)
            new_def.iteration = iteration

            if "system_prompt" in fixes:
                new_def.system_prompt = fixes["system_prompt"]
            if "retrieval_config" in fixes:
                rc = fixes["retrieval_config"]
                if isinstance(rc, dict):
                    new_def.retrieval_config = RetrievalConfig(
                        chunk_size=rc.get("chunk_size", new_def.retrieval_config.chunk_size),
                        chunk_overlap=rc.get("chunk_overlap", new_def.retrieval_config.chunk_overlap),
                        top_k=rc.get("top_k", new_def.retrieval_config.top_k),
                        score_threshold=rc.get("score_threshold", new_def.retrieval_config.score_threshold),
                    )
            if "tools" in fixes:
                new_def.tools = [t for t in fixes["tools"] if t in self.available_tools]

            return new_def
        except Exception:
            # If fix parsing fails, return original with minor prompt append
            new_def = current_definition.model_copy(deep=True)
            new_def.iteration = iteration
            new_def.system_prompt += f"\n\nADDITIONAL INSTRUCTION: {fix_instruction}"
            return new_def

    def _create_fallback_definition(
        self,
        requirements: RequirementsDocument,
        iteration: int
    ) -> AgentDefinition:
        """Create a basic fallback agent definition."""
        topics = ", ".join(requirements.must_answer_topics)
        refused = ", ".join(requirements.must_refuse_topics)
        warnings = ""
        if requirements.groundability_warnings:
            warnings = (
                "\n\nIMPORTANT LIMITATIONS: The following topics were requested but are "
                "NOT supported by available documents. You MUST NOT answer questions about: "
                + ", ".join(requirements.groundability_warnings)
            )

        system_prompt = f"""You are an AI assistant specialized in {requirements.scope}.

AUDIENCE: {requirements.audience}
TONE: {requirements.tone}

TOPICS YOU MUST ANSWER:
{topics}

TOPICS YOU MUST REFUSE:
{refused}
{warnings}

RULES:
1. ALWAYS base your answers on the provided document context.
2. ALWAYS cite the source document when answering.
3. If the question is outside your scope, politely refuse.
4. If you don't have enough information, say so honestly.
5. Never make up information not found in your documents.
"""

        return AgentDefinition(
            name=f"{requirements.scope} Agent",
            system_prompt=system_prompt,
            retrieval_config=RetrievalConfig(),
            tools=[t for t in requirements.tools_needed if t in self.available_tools],
            output_contract=OutputContract(
                refusal_template=f"I can only answer questions about {requirements.scope}. "
                                 f"This question is outside my scope."
            ),
            iteration=iteration
        )
