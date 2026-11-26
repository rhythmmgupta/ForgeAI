"""
Agent Runner (Core Requirement #8)
====================================
A minimal generic chat runner that loads any produced agent definition
and runs it with RAG retrieval and optional tool use.
"""

import json
from typing import List, Dict, Optional, Tuple

try:
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
except ImportError:
    from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_community.vectorstores import FAISS

from forgeai.config import LLMConfig, EmbeddingConfig, get_llm, get_embeddings
from forgeai.models import AgentDefinition
from forgeai.tools.registry import ToolRegistry
from forgeai.core.document_processor import load_documents, chunk_documents, create_vector_store


class AgentRunner:
    """
    Core Requirement #8: Runnable Product
    A generic runner that can load and run ANY produced agent definition.
    """

    def __init__(
        self,
        agent_definition: AgentDefinition,
        llm_config: LLMConfig,
        embedding_config: EmbeddingConfig,
        doc_folder: str,
        tool_registry: Optional[ToolRegistry] = None
    ):
        self.definition = agent_definition
        self.llm = get_llm(llm_config)
        self.tool_registry = tool_registry or ToolRegistry()
        self.chat_history: List[Dict[str, str]] = []
        self.vector_store: Optional[FAISS] = None

        # Build vector store from documents
        self._build_vector_store(doc_folder, embedding_config)

    def _build_vector_store(self, doc_folder: str, embedding_config: EmbeddingConfig):
        """Load documents and build the vector store."""
        documents = load_documents(doc_folder)
        chunks = chunk_documents(
            documents,
            chunk_size=self.definition.retrieval_config.chunk_size,
            chunk_overlap=self.definition.retrieval_config.chunk_overlap
        )
        self.vector_store = create_vector_store(chunks, embedding_config)
        self.chunks = chunks

    def query(self, question: str, return_context: bool = False) -> Tuple[str, List[str]]:
        """
        Process a user query through the full RAG pipeline.
        
        Args:
            question: User's natural language question
            return_context: Whether to return retrieved context
            
        Returns:
            Tuple of (answer, retrieved_chunks)
        """
        # 1. Retrieve relevant chunks
        retrieved_docs = self.vector_store.similarity_search_with_score(
            question,
            k=self.definition.retrieval_config.top_k
        )

        # Filter by score threshold
        relevant_chunks = []
        source_info = []
        for doc, score in retrieved_docs:
            # FAISS uses L2 distance, lower is better
            if score <= (2.0 - self.definition.retrieval_config.score_threshold * 2):
                relevant_chunks.append(doc.page_content)
                source = doc.metadata.get("source", "Unknown")
                page = doc.metadata.get("page", "")
                page_str = f" (Page {page})" if page else ""
                source_info.append(f"{source}{page_str}")

        # If no chunks pass threshold, use top results anyway
        if not relevant_chunks and retrieved_docs:
            for doc, score in retrieved_docs[:3]:
                relevant_chunks.append(doc.page_content)
                source = doc.metadata.get("source", "Unknown")
                page = doc.metadata.get("page", "")
                page_str = f" (Page {page})" if page else ""
                source_info.append(f"{source}{page_str}")

        # 2. Check if any tools should be invoked
        tool_results = self._check_tools(question)

        # 3. Build context
        context = "\n\n---\n\n".join(relevant_chunks) if relevant_chunks else "(No relevant context found)"
        if tool_results:
            context += f"\n\n--- Tool Results ---\n{tool_results}"

        # 4. Build messages
        source_list = ", ".join(set(source_info)) if source_info else "No sources"

        messages = [
            SystemMessage(content=self.definition.system_prompt),
        ]

        # Add chat history (memory)
        for msg in self.chat_history[-6:]:  # Keep last 6 messages for context
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        # Add current question with context
        messages.append(HumanMessage(content=(
            f"Context from documents:\n{context}\n\n"
            f"Sources: {source_list}\n\n"
            f"Question: {question}\n\n"
            f"Answer based on the provided context. Cite your sources."
        )))

        # 5. Generate response
        try:
            response = self.llm.invoke(messages)
            answer = response.content
        except Exception as e:
            answer = f"I encountered an error processing your question: {str(e)}"

        # 6. Update chat history
        self.chat_history.append({"role": "user", "content": question})
        self.chat_history.append({"role": "assistant", "content": answer})

        return answer, relevant_chunks

    def _check_tools(self, question: str) -> str:
        """Check if any attached tools should be invoked for this question."""
        if not self.definition.tools:
            return ""

        results = []
        question_lower = question.lower()

        for tool_name in self.definition.tools:
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                continue

            # Simple keyword matching to decide tool invocation
            if tool_name == "current_date" and any(
                w in question_lower for w in ["today", "current date", "what day", "date today"]
            ):
                results.append(self.tool_registry.execute_tool("current_date"))

            elif tool_name == "calculator" and any(
                w in question_lower for w in ["calculate", "compute", "how much", "total", "sum"]
            ):
                # Extract potential expression (basic)
                import re
                nums = re.findall(r'[\d.]+\s*[+\-*/]\s*[\d.]+', question)
                if nums:
                    results.append(self.tool_registry.execute_tool("calculator", expression=nums[0]))

            elif tool_name == "weather_api" and any(
                w in question_lower for w in ["weather", "temperature", "wind"]
            ):
                results.append(self.tool_registry.execute_tool(
                    "weather_api", location="requested location"
                ))

        return "\n".join(results)

    def reset_history(self):
        """Clear chat history."""
        self.chat_history = []


class AgentRunnerFromFile:
    """Load and run an agent from a saved definition file."""

    @staticmethod
    def load(
        definition_path: str,
        doc_folder: str,
        llm_config: LLMConfig,
        embedding_config: EmbeddingConfig
    ) -> AgentRunner:
        """Load an agent definition from a JSON file and create a runner."""
        with open(definition_path, "r") as f:
            data = json.load(f)

        definition = AgentDefinition(**data)
        return AgentRunner(
            agent_definition=definition,
            llm_config=llm_config,
            embedding_config=embedding_config,
            doc_folder=doc_folder
        )
