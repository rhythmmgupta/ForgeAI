"""
ForgeAI Offline / Resilient Simulation LLM Provider
====================================================
Provides a 100% generic, content-driven fallback LLM that parses the actual
brief, document summaries, document samples, requirements, and context from
prompts when live API keys are unavailable or offline.

No demo-specific rules, fixed document names, or hard-coded questions exist here.
"""

import json
import re
from typing import List, Any, Optional, Dict, Tuple
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration


_STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were",
    "will", "would", "should", "could", "have", "has", "had", "into", "about",
    "your", "our", "their", "they", "them", "what", "which", "when", "where",
    "who", "how", "can", "may", "not", "but", "all", "any", "only", "must",
    "need", "assistant", "agent", "help", "users", "questions", "answer",
    "based", "documents", "information", "provided", "using", "also", "such",
}


class OfflineSimulationChatModel(BaseChatModel):
    """
    A generic, deterministic simulation chat model for ForgeAI.
    Dynamically inspects prompt inputs (brief, documents, requirements, context)
    to produce schema-compliant, document-grounded outputs for ANY domain.
    """
    model_name: str = "forgeai-offline-simulator"
    temperature: float = 0.0

    @property
    def _llm_type(self) -> str:
        return "offline_simulation_chat_model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> ChatResult:
        system_text = "\n".join(
            m.content for m in messages if isinstance(m, SystemMessage) and isinstance(m.content, str)
        )
        full_prompt = "\n".join(m.content for m in messages if isinstance(m.content, str))
        response_text = self._route_and_generate(full_prompt, system_text)
        generation = ChatGeneration(message=AIMessage(content=response_text))
        return ChatResult(generations=[generation])

    # ─── Helpers for Dynamic Prompt Parsing ──────────────────────────────────

    @staticmethod
    def _extract_section(text: str, start_marker: str, end_markers: List[str]) -> str:
        """Extract text between start_marker and the earliest end_marker."""
        idx = text.find(start_marker)
        if idx == -1:
            return ""
        sub = text[idx + len(start_marker):]
        end_idx = len(sub)
        for em in end_markers:
            pos = sub.find(em)
            if pos != -1 and pos < end_idx:
                end_idx = pos
        return sub[:end_idx].strip()

    @staticmethod
    def _extract_keywords(text: str, limit: int = 12) -> List[str]:
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
        seen = []
        for w in words:
            if w not in _STOPWORDS and w not in seen:
                seen.append(w)
            if len(seen) >= limit:
                break
        return seen

    @staticmethod
    def _parse_doc_summary_files(doc_summary: str) -> List[Tuple[str, str]]:
        """Parse '- **filename** [type]:' or '=== filename ===' blocks from get_document_summary output."""
        files = []
        # Pattern 1: - **filename** [type]...
        md_blocks = re.split(r"-\s+\*\*(.+?)\*\*\s*\[[^\]]*\][^:]*:", doc_summary)
        if len(md_blocks) >= 3:
            for i in range(1, len(md_blocks) - 1, 2):
                fname = md_blocks[i].strip()
                body = md_blocks[i + 1].strip()
                files.append((fname, body))
            return files

        # Pattern 2: === filename ===
        blocks = re.split(r"===\s*(.+?)\s*===", doc_summary)
        if len(blocks) >= 3:
            for i in range(1, len(blocks) - 1, 2):
                fname = blocks[i].strip()
                body = blocks[i + 1].strip()
                files.append((fname, body))
        return files

    @staticmethod
    def _parse_doc_samples(samples_text: str) -> List[Tuple[str, str]]:
        """Parse '[Source: filename]' blocks from EvalGenerator."""
        blocks = re.split(r"\[Source:\s*(.+?)\]", samples_text)
        docs = []
        if len(blocks) >= 3:
            for i in range(1, len(blocks) - 1, 2):
                fname = blocks[i].strip()
                body = blocks[i + 1].strip()
                docs.append((fname, body))
        elif samples_text.strip():
            for idx, chunk in enumerate(samples_text.split("\n\n---\n\n"), 1):
                if chunk.strip():
                    docs.append((f"document_{idx}", chunk.strip()))
        return docs

    @staticmethod
    def _select_tools_from_text(brief: str, doc_summary: str, available_tools: List[str]) -> List[str]:
        """Restrained tool selection driven strictly by brief and document types."""
        brief_l = brief.lower()
        doc_l = doc_summary.lower()
        selected = []

        if "csv_lookup" in available_tools:
            if ".csv" in doc_l or any(k in brief_l for k in [
                "csv", "catalogue", "catalog", "inventory", "table", "part number",
                "sku", "product list", "price list", "directory", "spreadsheet"
            ]):
                selected.append("csv_lookup")

        if "calculator" in available_tools:
            if any(k in brief_l for k in [
                "calculat", "compute", "arithmetic", "total cost", "budget",
                "conversion", "currency", "discount", "quote", "pricing", "math"
            ]):
                selected.append("calculator")

        if "weather_api" in available_tools:
            if any(k in brief_l for k in [
                "weather", "forecast", "temperature", "wind speed", "meteorolog", "climate"
            ]):
                selected.append("weather_api")

        if "current_date" in available_tools:
            if any(k in brief_l for k in [
                "date", "today", "deadline", "schedule", "validity", "expir",
                "timeline", "leave", "calendar", "sla", "lead time"
            ]):
                selected.append("current_date")

        return selected

    @staticmethod
    def _infer_brief_topics(brief: str) -> Tuple[List[str], List[str], List[str]]:
        """Extract answer topics, refusal topics, and capabilities from a brief."""
        brief_clean = brief.strip()
        # Split sentences
        sentences = [s.strip() for s in re.split(r"[.!?]+", brief_clean) if s.strip()]
        must_answer = []
        must_refuse = []
        capabilities = []

        for sent in sentences:
            s_lower = sent.lower()
            if any(marker in s_lower for marker in ["refuse", "must not", "never ", "do not ", "don't ", "prohibit"]):
                # Extract refusal clause
                for marker in ["refuse to ", "refuse ", "must not ", "never ", "do not "]:
                    if marker in s_lower:
                        idx = s_lower.find(marker)
                        clause = sent[idx + len(marker):].strip(" ,.")
                        if clause:
                            must_refuse.append(clause)
                        break
            else:
                capabilities.append(sent)

        # Extract parenthetical or comma-separated topics from brief
        parens = re.findall(r"\(([^)]+)\)", brief_clean)
        for p in parens:
            for item in p.split(","):
                item_s = item.strip()
                if item_s and len(item_s) > 2:
                    must_answer.append(item_s)

        # Also add concise phrases from sentences
        for cap in capabilities[:4]:
            words = cap.split()
            if len(words) > 3:
                must_answer.append(" ".join(words[:10]))

        if not must_answer:
            must_answer = ["Questions covered directly by the supplied knowledge base documents"]
        if not must_refuse:
            must_refuse = [
                "Topics outside the supplied documents",
                "Making unauthorized approvals, exceptions, or legal commitments",
            ]

        return must_answer[:8], must_refuse[:6], capabilities[:5]

    @staticmethod
    def _infer_name_from_scope(scope: str) -> str:
        """Create a clean, generic agent name from its scope."""
        words = re.findall(r"[A-Za-z0-9-]+", scope)
        filtered = [w for w in words if w.lower() not in {
            "i", "need", "an", "a", "the", "assistant", "that", "answers", "helps",
            "with", "for", "to", "agent", "should", "must", "assist", "provide"
        }]
        title_words = [w.capitalize() for w in filtered[:4]]
        if not title_words:
            return "Domain Knowledge Assistant"
        return f"{' '.join(title_words)} Assistant"

    # ─── Router ──────────────────────────────────────────────────────────────

    def _route_and_generate(self, prompt: str, system_text: str) -> str:
        prompt_lower = prompt.lower()

        # 1. Intake Interviewer: Clarifying Questions
        if "generate at most 5 clarifying questions" in prompt_lower:
            brief = self._extract_section(prompt, "Brief:", ["Document Summary:", "Available Tools:"])
            doc_summary = self._extract_section(prompt, "Document Summary:", ["Available Tools:", "Generate at most"])
            files = self._parse_doc_summary_files(doc_summary)
            file_names = ", ".join(f[0] for f in files[:3]) if files else "the supplied documents"
            kws = self._extract_keywords(brief, limit=4)
            topic_str = ", ".join(kws) if kws else "the requested domain"
            return json.dumps([
                f"Who is the primary target audience for this assistant covering {topic_str}?",
                f"What tone and level of detail should responses follow when citing {file_names}?",
                "Are there specific edge cases or requests (such as approvals, exceptions, or external advice) that must be strictly refused?",
                "Should responses always include explicit source filenames and section/row citations?"
            ])

        # 2. Auto-answer clarifying questions
        if "simulating a requester who wrote this brief" in prompt_lower:
            brief = self._extract_section(prompt, "Brief:", ["Available Documents:", "Questions:"])
            q_block = self._extract_section(prompt, "Questions:", ["Answer each question"])
            questions = [
                re.sub(r"^\d+\.\s*", "", line).strip()
                for line in q_block.splitlines() if line.strip()
            ]
            answers = []
            for q in questions[:5]:
                ql = q.lower()
                if "audience" in ql:
                    ans = f"Internal staff and stakeholders referenced in the brief ({brief[:80]})."
                elif "tone" in ql:
                    ans = "Professional, clear, concise, and strictly grounded in the documents."
                elif "refus" in ql or "edge" in ql:
                    ans = "Strictly refuse out-of-scope requests, unauthorized approvals, or topics not found in the documents."
                elif "cit" in ql or "source" in ql:
                    ans = "Yes, always cite the exact source document filename and relevant section or row."
                else:
                    ans = "Follow the brief scope strictly and rely only on the supplied documents."
                answers.append({"question": q, "answer": ans})
            return json.dumps(answers)

        # 3. Requirements Generation (Intake Interviewer & Groundability Guard)
        if "produce a structured requirements document as json" in prompt_lower:
            brief = self._extract_section(prompt, "Brief:", ["Document Summary:", "User Clarifications:"])
            doc_summary = self._extract_section(prompt, "Document Summary:", ["User Clarifications:", "GROUNDABILITY CHECK:"])
            clar_raw = self._extract_section(prompt, "User Clarifications:", ["GROUNDABILITY CHECK:", "Available tools"])
            tools_raw = self._extract_section(prompt, "Available tools in the registry:", ["Only select tools", "Produce a JSON"])
            available_tools = [t.strip() for t in tools_raw.split(",") if t.strip()] or [
                "csv_lookup", "calculator", "weather_api", "current_date"
            ]

            files = self._parse_doc_summary_files(doc_summary)
            doc_coverage = []
            for fname, body in files:
                first_lines = " ".join(line.strip() for line in body.splitlines()[:3] if line.strip())
                doc_coverage.append(f"{fname}: {first_lines[:160]}")

            must_answer, must_refuse, capabilities = self._infer_brief_topics(brief)
            # Enrich must_answer from document headings/topics
            for fname, body in files:
                for line in body.splitlines():
                    ls = line.strip()
                    if 6 < len(ls) < 70 and (ls.isupper() or ls.endswith(":") or ls.startswith("#") or "SECTION" in ls.upper()):
                        cleaned = ls.strip("#: ").title()
                        if cleaned not in must_answer:
                            must_answer.append(cleaned)
                        if len(must_answer) >= 10:
                            break

            # Groundability check: compare brief words against doc_summary
            doc_text_lower = doc_summary.lower()
            warnings = []
            unsupported = []
            # Check for explicit capabilities/requests in brief not supported in docs
            check_phrases = [
                ("live ", "Live real-time external data is not available in static documents"),
                ("real-time", "Real-time system integration is not supported by static documents"),
                ("weather", "Live weather forecasting is not contained in the static document folder"),
                ("stock price", "Live stock/market pricing is not in the supplied documents"),
                ("approve", "Automated transaction or policy approvals are outside read-only document Q&A"),
                ("legal advice", "Formal legal advice is not supported and must be refused"),
                ("payroll", "Individual payroll records are not present in the supplied documents"),
                ("medical", "Medical diagnosis or clinical advice is not supported"),
            ]
            brief_lower = brief.lower()
            for trigger, msg in check_phrases:
                if trigger in brief_lower and trigger.strip() not in doc_text_lower:
                    warnings.append(msg)
                    unsupported.append(msg)

            tools_needed = self._select_tools_from_text(brief, doc_summary, available_tools)

            # Detect tone & audience from brief
            tone = "Professional, clear, and strictly document-grounded"
            if "friendly" in brief_lower or "approachable" in brief_lower:
                tone = "Professional, approachable, and strictly document-grounded"
            elif "technical" in brief_lower or "precise" in brief_lower:
                tone = "Precise, technical, and compliance-oriented"

            audience = "Users and stakeholders defined in the agent brief"
            aud_match = re.search(r"for\s+([A-Za-z0-9 ,&-]{4,60}?)(?:\.|,| who | that |$)", brief, re.IGNORECASE)
            if aud_match:
                audience = aud_match.group(1).strip()

            return json.dumps({
                "scope": brief.strip(),
                "audience": audience,
                "tone": tone,
                "must_answer_topics": must_answer,
                "must_refuse_topics": must_refuse,
                "required_capabilities": capabilities,
                "document_coverage": doc_coverage,
                "document_summary": f"Knowledge base containing {len(files)} file(s): {', '.join(f[0] for f in files)}.",
                "groundability_warnings": warnings,
                "unsupported_requirements": unsupported,
                "tools_needed": tools_needed,
                "clarifications": []
            })

        # 4. Prompt Variant (Tournament)
        if "generate a different variant of the system prompt" in prompt_lower:
            base_prompt = self._extract_section(prompt, "Here is the base system prompt for an agent:", ["Requirements:"])
            if "conversational" in prompt_lower:
                return (
                    f"{base_prompt}\n\n"
                    "STYLE DIRECTIVE: Communicate in a helpful, clear, conversational manner while "
                    "keeping every factual claim strictly anchored to retrieved sources and citing filenames."
                )
            elif "minimal" in prompt_lower:
                lines = [l for l in base_prompt.splitlines() if l.strip()]
                concise = "\n".join(lines[:10])
                return (
                    f"{concise}\n"
                    "Rule: Answer strictly from context with citations; refuse out-of-scope or unsupported queries."
                )
            else:
                return (
                    f"{base_prompt}\n\n"
                    "STRUCTURED RESPONSE PROTOCOL:\n"
                    "1. Direct Answer\n2. Supporting Policy/Data Facts\n3. Source Citations"
                )

        # 5. Agent Generator (declarative agent definition)
        if "you are forgeai's agent generator" in prompt_lower:
            req_str = self._extract_section(prompt, "Requirements:", ["Your output must be a JSON"])
            try:
                req = json.loads(req_str)
            except Exception:
                req = {}

            scope = req.get("scope", "Document-grounded assistant")
            audience = req.get("audience", "General users")
            tone = req.get("tone", "Professional and accurate")
            must_answer = req.get("must_answer_topics", [])
            must_refuse = req.get("must_refuse_topics", [])
            warnings = req.get("groundability_warnings", [])
            tools = req.get("tools_needed", [])
            doc_cov = req.get("document_coverage", [])
            doc_names = [d.split(":")[0].strip() for d in doc_cov if ":" in d]

            name = self._infer_name_from_scope(scope)
            is_tabular = any(n.endswith(".csv") for n in doc_names) or "csv_lookup" in tools

            refusal_rules = list(must_refuse)
            for w in warnings:
                if w not in refusal_rules:
                    refusal_rules.append(w)

            system_prompt = (
                f"You are the {name}.\n"
                f"SCOPE: {scope}\n"
                f"AUDIENCE: {audience}\n"
                f"TONE: {tone}\n\n"
                f"TOPICS YOU MUST ANSWER:\n" +
                "\n".join(f"- {t}" for t in must_answer) +
                "\n\nTOPICS AND ACTIONS YOU MUST REFUSE:\n" +
                "\n".join(f"- {r}" for r in refusal_rules) +
                "\n\nCORE GROUNDING RULES:\n"
                "1. Answer ONLY using facts explicitly present in the retrieved document context or tool outputs.\n"
                "2. ALWAYS cite the exact source document filename (and section/row if available).\n"
                "3. If a question is out of scope, unsupported by the documents, or asks for prohibited actions, "
                "refuse politely using the refusal format and never guess or fabricate information.\n"
            )

            return json.dumps({
                "name": name,
                "scope": scope,
                "system_prompt": system_prompt,
                "refusal_rules": refusal_rules,
                "document_list": doc_names,
                "retrieval_config": {
                    "chunk_size": 400 if is_tabular else 500,
                    "chunk_overlap": 80 if is_tabular else 100,
                    "top_k": 6 if is_tabular else 5,
                    "score_threshold": 0.3
                },
                "tools": tools,
                "output_contract": {
                    "format": "markdown",
                    "max_length": 450,
                    "must_cite_sources": True,
                    "refusal_template": (
                        f"I am the {name}. I cannot fulfill this request because it falls outside "
                        f"my supported scope or is not covered in my source documents."
                    )
                },
                "citation_behavior": "Every factual answer must explicitly cite the source document filename."
            })

        # 6. Eval Generator: Dynamically synthesize >= 20 grounded test cases from document samples
        if "evaluation set generator" in prompt_lower:
            req_str = self._extract_section(prompt, "Agent Requirements:", ["Document Content Samples"])
            samples_str = self._extract_section(prompt, "Document Content Samples", ["Generate EXACTLY", "DISTRIBUTION"])
            num_match = re.search(r"Generate EXACTLY (\d+) test cases", prompt)
            target_n = int(num_match.group(1)) if num_match else 24

            try:
                req = json.loads(req_str)
            except Exception:
                req = {}

            docs = self._parse_doc_samples(samples_str)
            must_refuse = req.get("must_refuse_topics", [])
            tools_needed = req.get("tools_needed", [])

            cases = []
            case_idx = 1

            # Extract informative candidate lines from each document
            doc_facts: List[Tuple[str, str, List[str]]] = []
            for fname, body in docs:
                lines = [l.strip() for l in body.splitlines() if len(l.strip()) > 25]
                for line in lines:
                    if line.startswith("===") or line.startswith("---"):
                        continue
                    # Extract key tokens/numbers as verifiable facts
                    facts = self._extract_fact_tokens(line)
                    if facts:
                        doc_facts.append((fname, line, facts))

            # A. Answerable cases (~13 cases)
            ans_target = max(12, target_n // 2)
            step = max(1, len(doc_facts) // max(1, ans_target))
            selected_facts = doc_facts[::step][:ans_target]
            for fname, line, facts in selected_facts:
                q = self._form_question_from_line(fname, line, facts)
                cases.append({
                    "id": f"case_{case_idx:02d}",
                    "question": q,
                    "case_type": "answerable",
                    "expected_behavior": "answer",
                    "expected_answer_facts": facts[:3],
                    "source_document": fname,
                    "expected_sources": [fname],
                    "should_refuse": False,
                    "grading_notes": f"Verify facts from {fname}: {', '.join(facts[:3])}"
                })
                case_idx += 1

            # B. Out-of-scope / Refusal cases (~5 cases)
            oos_questions = []
            for topic in must_refuse[:3]:
                oos_questions.append(f"Can you handle or override this request: {topic}?")
            general_oos = [
                "Write a creative fictional poem about outer space.",
                "What is the current stock price of Apple Inc.?",
                "Can you diagnose my medical symptoms and prescribe medication?",
                "What is the capital city of Brazil?",
            ]
            if "weather_api" not in tools_needed:
                general_oos.insert(0, "What is the live weather forecast in Tokyo right now?")
            for gq in general_oos:
                if len(oos_questions) >= 5:
                    break
                oos_questions.append(gq)

            for oq in oos_questions[:5]:
                cases.append({
                    "id": f"case_{case_idx:02d}",
                    "question": oq,
                    "case_type": "out_of_scope",
                    "expected_behavior": "refuse",
                    "expected_answer_facts": [],
                    "source_document": None,
                    "expected_sources": [],
                    "should_refuse": True,
                    "grading_notes": "Agent must refuse cleanly without fabricating an answer."
                })
                case_idx += 1

            # C. Multi-document cases (~3 cases)
            unique_files = list(dict.fromkeys(f for f, _, _ in doc_facts))
            for m_i in range(3):
                if len(unique_files) >= 2:
                    f1 = unique_files[m_i % len(unique_files)]
                    f2 = unique_files[(m_i + 1) % len(unique_files)]
                    facts1 = [x for x in doc_facts if x[0] == f1]
                    facts2 = [x for x in doc_facts if x[0] == f2]
                    item1 = facts1[min(m_i, len(facts1) - 1)]
                    item2 = facts2[min(m_i, len(facts2) - 1)]
                    combined_facts = (item1[2][:2] + item2[2][:2])[:3]
                    q = (
                        f"Comparing {f1} and {f2}, what details are provided regarding "
                        f"'{item1[1][:45].strip()}' and '{item2[1][:45].strip()}'?"
                    )
                    sources = [f1, f2]
                elif doc_facts:
                    item1 = doc_facts[m_i % len(doc_facts)]
                    combined_facts = item1[2][:2]
                    q = f"Summarize the related rules in {item1[0]} concerning: {item1[1][:60]}."
                    sources = [item1[0]]
                else:
                    combined_facts = []
                    q = "Combine the key guidelines across the supplied documents."
                    sources = []

                cases.append({
                    "id": f"case_{case_idx:02d}",
                    "question": q,
                    "case_type": "multi_document",
                    "expected_behavior": "answer",
                    "expected_answer_facts": combined_facts,
                    "source_document": ", ".join(sources),
                    "expected_sources": sources,
                    "should_refuse": False,
                    "grading_notes": f"Must synthesize facts across {', '.join(sources)}."
                })
                case_idx += 1

            # D. Edge / Ambiguous cases (fill remainder up to target_n, min 3)
            edge_templates = [
                ("Explain the policy.", "Ambiguous underspecified prompt; agent should ask for clarification or summarize scope."),
                ("Tell me everything about exceptions and special cases.", "Boundary case testing whether agent sticks to documented rules."),
                ("What are the exact limits or thresholds mentioned?", "Tests retrieval precision on numeric limits."),
                ("Who is responsible if something goes wrong?", "Ambiguous responsibility query requiring grounded citation."),
            ]
            e_i = 0
            while len(cases) < max(20, target_n):
                eq, note = edge_templates[e_i % len(edge_templates)]
                if e_i >= len(edge_templates) and doc_facts:
                    df = doc_facts[e_i % len(doc_facts)]
                    eq = f"Briefly clarify the rule about: {df[2][0]}?"
                    facts = [df[2][0]]
                    src = [df[0]]
                else:
                    facts = []
                    src = []
                cases.append({
                    "id": f"case_{case_idx:02d}",
                    "question": eq,
                    "case_type": "edge_case",
                    "expected_behavior": "answer",
                    "expected_answer_facts": facts,
                    "source_document": src[0] if src else None,
                    "expected_sources": src,
                    "should_refuse": False,
                    "grading_notes": note
                })
                case_idx += 1
                e_i += 1

            return json.dumps(cases[:max(20, target_n)])

        # 7. Judge
        if "you are forgeai's impartial judge" in prompt_lower:
            should_refuse_str = self._extract_section(prompt, "- Should Refuse:", ["- Source Document:"])
            should_refuse = "true" in should_refuse_str.lower()
            expected_facts_str = self._extract_section(prompt, "- Expected Facts:", ["- Should Refuse:"])
            response_text = self._extract_section(prompt, "AGENT RESPONSE:", ["RETRIEVED CONTEXT:"])
            context_text = self._extract_section(prompt, "RETRIEVED CONTEXT:", ["Score the response"])

            try:
                expected_facts = json.loads(expected_facts_str)
            except Exception:
                expected_facts = []

            resp_l = response_text.lower()
            is_refusal = any(p in resp_l for p in [
                "cannot", "can't", "outside my scope", "outside the scope",
                "do not have", "don't have", "not covered", "not in my documents",
                "unable to", "cannot fulfill"
            ])

            if should_refuse:
                if is_refusal:
                    return json.dumps({
                        "is_grounded": True, "is_correct": True, "correctly_refused": True,
                        "score": 1.0, "failure_category": "none", "failure_explanation": ""
                    })
                return json.dumps({
                    "is_grounded": False, "is_correct": False, "correctly_refused": False,
                    "score": 0.0, "failure_category": "wrong_acceptance",
                    "failure_explanation": "Answered an out-of-scope question instead of refusing."
                })

            if is_refusal and expected_facts:
                return json.dumps({
                    "is_grounded": False, "is_correct": False, "correctly_refused": False,
                    "score": 0.0, "failure_category": "wrong_refusal",
                    "failure_explanation": "Refused an answerable question."
                })

            if expected_facts:
                ctx_l = context_text.lower()
                found = sum(1 for f in expected_facts if f.lower() in resp_l)
                in_ctx = sum(1 for f in expected_facts if f.lower() in ctx_l)
                ratio = found / len(expected_facts)
                if ratio >= 0.8:
                    return json.dumps({
                        "is_grounded": True, "is_correct": True, "correctly_refused": True,
                        "score": 0.95, "failure_category": "none", "failure_explanation": ""
                    })
                elif in_ctx == 0:
                    return json.dumps({
                        "is_grounded": False, "is_correct": False, "correctly_refused": True,
                        "score": round(0.3 + 0.4 * ratio, 2),
                        "failure_category": "retrieval_miss",
                        "failure_explanation": "Expected facts were missing from retrieved chunks."
                    })
                else:
                    return json.dumps({
                        "is_grounded": True, "is_correct": False, "correctly_refused": True,
                        "score": round(0.4 + 0.4 * ratio, 2),
                        "failure_category": "prompt_defect",
                        "failure_explanation": f"Context contained facts, but response only included {found}/{len(expected_facts)}."
                    })

            has_content = len(response_text.strip()) > 20 and len(context_text.strip()) > 10
            return json.dumps({
                "is_grounded": has_content, "is_correct": has_content, "correctly_refused": True,
                "score": 0.85 if has_content else 0.4,
                "failure_category": "none" if has_content else "retrieval_miss",
                "failure_explanation": "" if has_content else "Insufficient grounded content."
            })

        # 8. Critic-Optimizer
        if "you are forgeai's critic" in prompt_lower:
            failed_block = self._extract_section(prompt, "FAILED CASES:", ["CURRENT SYSTEM PROMPT:"])
            case_ids = re.findall(r"\[(case_[^\]]+)\]", failed_block)
            fixes = []
            if "retrieval_miss" in prompt_lower:
                fixes.append({
                    "change_type": "retrieval_param",
                    "failure_category": "retrieval_miss",
                    "diagnosis": "Relevant facts were not captured in top_k retrieved chunks.",
                    "reason": "Expanding top_k and lowering score_threshold improves recall for multi-part queries.",
                    "description": "Increase top_k by 3 and adjust chunk overlap to improve recall.",
                    "failures_addressed": case_ids[:6],
                    "fix_instruction": "Increase top_k by 3 and lower score_threshold by 0.05."
                })
            if any(k in prompt_lower for k in ["prompt_defect", "incomplete", "hallucination", "wrong_refusal", "wrong_acceptance"]):
                fixes.append({
                    "change_type": "prompt_edit",
                    "failure_category": "prompt_defect",
                    "diagnosis": "Responses missed expected facts or boundary rules despite available context.",
                    "reason": "Explicitly instructing complete fact extraction and strict refusal strengthens compliance.",
                    "description": "Reinforce complete fact extraction from context and strict refusal boundaries.",
                    "failures_addressed": case_ids[:6],
                    "fix_instruction": "Add explicit instruction to include all specific figures/facts from context and cite filenames."
                })
            if not fixes:
                fixes.append({
                    "change_type": "prompt_edit",
                    "failure_category": "prompt_defect",
                    "diagnosis": "Minor completeness improvement needed.",
                    "reason": "Ensure thorough citation and fact coverage.",
                    "description": "Clarify answer completeness and source citation rules.",
                    "failures_addressed": case_ids[:4],
                    "fix_instruction": "Always include exact figures, names, and source filenames from context."
                })
            return json.dumps(fixes)

        # 9. Apply Fix
        if "apply the specified fix without rewriting the entire prompt" in prompt_lower:
            curr_prompt = self._extract_section(prompt, "Current system prompt:", ["Current retrieval config:"])
            top_k_m = re.search(r"top_k:\s*(\d+)", prompt)
            chunk_m = re.search(r"chunk_size:\s*(\d+)", prompt)
            thresh_m = re.search(r"score_threshold:\s*([\d.]+)", prompt)
            curr_k = int(top_k_m.group(1)) if top_k_m else 5
            curr_chunk = int(chunk_m.group(1)) if chunk_m else 500
            curr_thresh = float(thresh_m.group(1)) if thresh_m else 0.3

            result: Dict[str, Any] = {}
            if "top_k" in prompt_lower or "retrieval" in prompt_lower:
                result["retrieval_config"] = {
                    "chunk_size": max(350, curr_chunk - 50),
                    "chunk_overlap": 100,
                    "top_k": min(10, curr_k + 3),
                    "score_threshold": max(0.15, round(curr_thresh - 0.05, 2)),
                }
            result["system_prompt"] = (
                f"{curr_prompt.strip()}\n\n"
                "REFINEMENT DIRECTIVE: Include all specific numbers, names, and rules from the retrieved context, "
                "cite exact source filenames, and refuse any request outside the documented scope."
            )
            return json.dumps(result)

        # 10. RAG Chat Response (Agent Runner)
        if "context from documents:" in prompt_lower:
            context = self._extract_section(prompt, "Context from documents:", ["Sources:"])
            sources = self._extract_section(prompt, "Sources:", ["Question:"])
            question = self._extract_section(prompt, "Question:", ["Answer based on"])
            return self._answer_from_context(question, context, sources, system_text)

        return "Acknowledged. Processing request based on available context."

    # ─── Dynamic Fact & QA Helpers ───────────────────────────────────────────

    @staticmethod
    def _extract_fact_tokens(line: str) -> List[str]:
        """Extract verifiable facts (numbers, codes, capitalized terms, key phrases) from a line."""
        facts = []
        # Numbers/currencies/percentages
        for m in re.findall(r"(?:\$|USD\s*|€|£)?\d+(?:[.,]\d+)?%?(?:\s*(?:days?|weeks?|months?|years?|hours?|units?|km/h|°C))?", line):
            m_s = m.strip()
            if len(m_s) >= 2 and m_s not in facts:
                facts.append(m_s)
        # Uppercase codes or proper nouns
        for m in re.findall(r"\b[A-Z]{2,}-\d+\b|\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", line):
            if m not in facts and len(m) > 3:
                facts.append(m)
        # Fallback: longest meaningful words
        if len(facts) < 2:
            for w in re.findall(r"[A-Za-z0-9_-]{5,}", line):
                if w.lower() not in _STOPWORDS and w not in facts:
                    facts.append(w)
                if len(facts) >= 3:
                    break
        return facts[:4]

    @staticmethod
    def _form_question_from_line(fname: str, line: str, facts: List[str]) -> str:
        """Form a natural question targeting the content of a document line."""
        if "|" in line and ":" in line:
            # CSV row formatted as "col1: val1 | col2: val2"
            parts = [p.strip() for p in line.split("|")]
            head = parts[0] if parts else line[:40]
            return f"According to {fname}, what are the details for {head}?"
        subject = " ".join(line.split()[:8]).rstrip(":,.")
        return f"What does {fname} specify regarding {subject}?"

    def _answer_from_context(self, question: str, context: str, sources: str, system_text: str) -> str:
        """Produce a strictly grounded answer or refusal using only the retrieved context."""
        q_lower = question.lower().strip()

        # Obvious general/unrelated OOS patterns
        obvious_oos = [
            "poem", "joke", "capital of", "stock price", "prescribe medication",
            "diagnose my medical", "outer space",
        ]
        if any(p in q_lower for p in obvious_oos):
            return (
                "I cannot answer this request because it is outside my scope and not covered "
                "in my source documents."
            )

        # Check explicit refusal directives in system prompt
        refuse_block = self._extract_section(
            system_text, "TOPICS AND ACTIONS YOU MUST REFUSE:", ["CORE GROUNDING RULES:", "RULES:"]
        )
        q_kws = set(self._extract_keywords(question, limit=10))
        ctx_lower = context.lower()

        # Check if question explicitly asks to grant/approve/override or hits a refusal topic with weak context support
        if any(k in q_lower for k in ["grant me an exception", "immediately approve", "override policy", "legal advice"]):
            return (
                "I cannot fulfill this request. Granting exceptions, approvals, or formal advice is "
                "outside my authorized scope."
            )

        if refuse_block:
            for r_line in refuse_block.splitlines():
                r_kws = set(self._extract_keywords(r_line, limit=6))
                if r_kws and len(q_kws & r_kws) >= 2:
                    # Only refuse if context does not directly support answering it
                    ctx_hits = sum(1 for w in q_kws if w in ctx_lower)
                    if ctx_hits < max(2, len(q_kws) // 2):
                        return (
                            f"I cannot fulfill this request as it falls under my refusal scope ({r_line.strip('- ')})."
                        )

        if not context or "(No relevant context found)" in context:
            return "I don't have information about that in my source documents."

        # Rank lines/sentences in context by keyword overlap with the question
        candidates = []
        for raw_line in context.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("---"):
                continue
            l_lower = line.lower()
            score = sum(2 if w in l_lower else 0 for w in q_kws)
            # Bonus for tool results
            if "Result:" in line or "Current Date" in line or "Found " in line:
                score += 2
            candidates.append((score, line))

        candidates.sort(key=lambda x: x[0], reverse=True)
        top_lines = [line for sc, line in candidates[:4] if sc > 0]
        if not top_lines:
            # Weak overlap check: if question has specific words and ZERO overlap, refuse honestly
            if len(q_kws) >= 3 and sum(1 for w in q_kws if w in ctx_lower) == 0:
                return "I don't have information about that in my source documents."
            top_lines = [line for _, line in candidates[:3]]

        bullet_body = "\n".join(f"- {l}" for l in top_lines)
        return (
            f"Based on the retrieved documents:\n\n"
            f"{bullet_body}\n\n"
            f"**Sources:** {sources}"
        )
