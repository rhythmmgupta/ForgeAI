"""
ForgeAI Streamlit UI (Stretch Goal)
====================================
A web interface for the ForgeAI factory and the chat runner.
Provides both the factory interface (configure & run) and the
chat interface (interact with generated agents).
"""

import os
import json
import tempfile
import shutil
from pathlib import Path

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="ForgeAI — The Agent Factory",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)


def apply_theme():
    """Apply custom theme with dark/light toggle (stretch goal)."""
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = True

    if st.session_state.dark_mode:
        st.markdown("""
        <style>
        .stApp { background-color: #0e1117; color: #fafafa; }
        .stSidebar { background-color: #1a1f2e; }
        .success-box { background-color: #1a3a1a; padding: 15px; border-radius: 10px;
                       border-left: 4px solid #4caf50; margin: 10px 0; }
        .warning-box { background-color: #3a3a1a; padding: 15px; border-radius: 10px;
                       border-left: 4px solid #ff9800; margin: 10px 0; }
        .error-box { background-color: #3a1a1a; padding: 15px; border-radius: 10px;
                     border-left: 4px solid #f44336; margin: 10px 0; }
        .info-box { background-color: #1a2a3a; padding: 15px; border-radius: 10px;
                    border-left: 4px solid #2196f3; margin: 10px 0; }
        .metric-card { background-color: #1a1f2e; padding: 20px; border-radius: 10px;
                       text-align: center; border: 1px solid #333; }
        .source-highlight { background-color: #2a2a1a; padding: 10px; border-radius: 5px;
                           border-left: 3px solid #ffd700; margin: 5px 0; font-size: 0.85em; }
        .chat-user { background-color: #1a2a3a; padding: 12px 16px; border-radius: 15px 15px 5px 15px;
                     margin: 8px 0; max-width: 80%; margin-left: auto; }
        .chat-agent { background-color: #1a3a1a; padding: 12px 16px; border-radius: 15px 15px 15px 5px;
                      margin: 8px 0; max-width: 80%; }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        .stApp { background-color: #ffffff; color: #333333; }
        .success-box { background-color: #e8f5e9; padding: 15px; border-radius: 10px;
                       border-left: 4px solid #4caf50; margin: 10px 0; }
        .warning-box { background-color: #fff3e0; padding: 15px; border-radius: 10px;
                       border-left: 4px solid #ff9800; margin: 10px 0; }
        .error-box { background-color: #ffebee; padding: 15px; border-radius: 10px;
                     border-left: 4px solid #f44336; margin: 10px 0; }
        .info-box { background-color: #e3f2fd; padding: 15px; border-radius: 10px;
                    border-left: 4px solid #2196f3; margin: 10px 0; }
        .metric-card { background-color: #f5f5f5; padding: 20px; border-radius: 10px;
                       text-align: center; border: 1px solid #ddd; }
        .source-highlight { background-color: #fffde7; padding: 10px; border-radius: 5px;
                           border-left: 3px solid #ffd700; margin: 5px 0; font-size: 0.85em; }
        .chat-user { background-color: #e3f2fd; padding: 12px 16px; border-radius: 15px 15px 5px 15px;
                     margin: 8px 0; max-width: 80%; margin-left: auto; }
        .chat-agent { background-color: #e8f5e9; padding: 12px 16px; border-radius: 15px 15px 15px 5px;
                      margin: 8px 0; max-width: 80%; }
        </style>
        """, unsafe_allow_html=True)


def sidebar():
    """Render sidebar with navigation and settings."""
    with st.sidebar:
        st.title("🏭 ForgeAI")
        st.caption("The Agent That Builds Agents")
        st.divider()

        # Navigation
        page = st.radio(
            "Navigation",
            ["🏠 Home", "🔨 Build Agent", "💬 Chat with Agent", "📊 Reports"],
            label_visibility="collapsed"
        )

        st.divider()

        # Theme toggle (stretch goal)
        st.subheader("⚙️ Settings")
        dark_mode = st.toggle("🌙 Dark Mode", value=st.session_state.get("dark_mode", True))
        st.session_state.dark_mode = dark_mode

        # LLM Configuration
        st.subheader("🤖 LLM Config")
        provider = st.selectbox("Provider", ["groq", "gemini"])
        if provider == "groq":
            api_key = st.text_input("Groq API Key", type="password",
                                    value=os.getenv("GROQ_API_KEY", ""))
            model = st.selectbox("Model", [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768"
            ])
        else:
            api_key = st.text_input("Google API Key", type="password",
                                    value=os.getenv("GOOGLE_API_KEY", ""))
            model = st.selectbox("Model", [
                "gemini-2.0-flash",
                "gemini-1.5-flash"
            ])

        st.session_state.llm_provider = provider
        st.session_state.llm_model = model
        st.session_state.api_key = api_key

        return page


def home_page():
    """Render the home page."""
    st.title("🏭 ForgeAI — The Agent That Builds Agents")
    st.markdown("---")

    st.markdown("""
    ### What is ForgeAI?
    
    ForgeAI is an **autonomous agent factory** that takes:
    - A **one-paragraph brief** describing what agent you need
    - A **folder of documents** as the agent's knowledge base
    
    And produces:
    - A **working, tested AI agent** with system prompt, retrieval config, and tool selection
    - An **auto-generated evaluation set** with 20+ test cases
    - A **quality report** with honest assessment of strengths and failures
    
    ### Pipeline Architecture
    """)

    st.markdown("""
    ```
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │   1. Intake   │───▶│ 2. Ground-   │───▶│ 3. Agent     │
    │  Interviewer  │    │  ability     │    │  Generator   │
    └──────────────┘    │  Guard       │    └──────┬───────┘
                        └──────────────┘           │
    ┌──────────────┐    ┌──────────────┐    ┌──────▼───────┐
    │ 6. Critic-   │◀───│  5. Judge    │◀───│ 4. Eval      │
    │  Optimizer   │    │  (LLM+Det.)  │    │  Generator   │
    │  Loop (×3)   │    └──────────────┘    └──────────────┘
    └──────┬───────┘
           │
    ┌──────▼───────┐    ┌──────────────┐    ┌──────────────┐
    │ 7. Honest    │───▶│ 8. Runnable  │───▶│ 9. Demo      │
    │  Report      │    │  Product     │    │  Runs        │
    └──────────────┘    └──────────────┘    └──────────────┘
    ```
    """)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Core Requirements", "9/9", "Complete")
    with col2:
        st.metric("Stretch Goals", "5/6", "Attempted")
    with col3:
        st.metric("Demo Runs", "2", "Committed")
    with col4:
        st.metric("Tools Available", "4", "In Registry")


def build_page():
    """Render the Build Agent page."""
    st.title("🔨 Build a New Agent")
    st.markdown("---")

    # Check API key
    if not st.session_state.get("api_key"):
        st.warning("⚠️ Please enter your API key in the sidebar to continue.")
        return

    # Brief input
    st.subheader("📝 Agent Brief")
    brief = st.text_area(
        "Describe the agent you want in one paragraph:",
        height=100,
        placeholder="Example: I need an assistant that answers HR policy questions for shore staff, "
                    "covering leave policies, benefits, code of conduct, and grievance procedures."
    )

    # Document upload
    st.subheader("📄 Upload Documents")
    uploaded_files = st.file_uploader(
        "Upload PDF, CSV, or TXT files",
        type=["pdf", "csv", "txt", "md"],
        accept_multiple_files=True
    )

    # Advanced settings
    with st.expander("⚙️ Advanced Settings"):
        col1, col2 = st.columns(2)
        with col1:
            max_iterations = st.slider("Max Optimization Iterations", 1, 5, 3)
            run_tournament = st.checkbox("Run Prompt Tournament", value=True)
        with col2:
            num_eval_cases = st.slider("Number of Eval Cases", 10, 40, 24)
            human_checkpoint = st.checkbox("Human Checkpoint", value=False)

    # Run button
    if st.button("🚀 Build Agent", type="primary", use_container_width=True):
        if not brief:
            st.error("Please provide an agent brief.")
            return
        if not uploaded_files:
            st.error("Please upload at least one document.")
            return

        # Save uploaded files to temp directory
        doc_dir = tempfile.mkdtemp()
        for f in uploaded_files:
            file_path = Path(doc_dir) / f.name
            file_path.write_bytes(f.getvalue())

        output_dir = tempfile.mkdtemp()

        # Set environment variables
        provider = st.session_state.get("llm_provider", "groq")
        if provider == "groq":
            os.environ["GROQ_API_KEY"] = st.session_state.get("api_key", "")
        else:
            os.environ["GOOGLE_API_KEY"] = st.session_state.get("api_key", "")
        os.environ["LLM_PROVIDER"] = provider
        os.environ["LLM_MODEL"] = st.session_state.get("llm_model", "llama-3.3-70b-versatile")

        # Run pipeline
        try:
            from forgeai.config import ForgeAIConfig, LLMConfig, BudgetConfig
            from forgeai.pipeline import ForgeAIPipeline

            config = ForgeAIConfig(
                llm=LLMConfig(
                    provider=provider,
                    model=st.session_state.get("llm_model", "llama-3.3-70b-versatile"),
                    groq_api_key=st.session_state.get("api_key") if provider == "groq" else None,
                    google_api_key=st.session_state.get("api_key") if provider == "gemini" else None,
                ),
                budget=BudgetConfig(max_iterations=max_iterations)
            )

            pipeline = ForgeAIPipeline(config)

            with st.status("🏭 ForgeAI Pipeline Running...", expanded=True) as status:
                st.write("📋 Stage 1 & 2: Intake Interview & Groundability Guard...")
                report = pipeline.run(
                    brief=brief,
                    doc_folder=doc_dir,
                    output_dir=output_dir,
                    auto_mode=True,
                    run_tournament=run_tournament,
                )
                status.update(label="✅ Pipeline Complete!", state="complete")

            # Display results
            st.success(f"Agent built successfully! Final Score: {report.final_score:.1%}")

            # Save to session state for chat
            st.session_state.last_report = report
            st.session_state.last_doc_folder = doc_dir
            st.session_state.last_output_dir = output_dir

            # Show report
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Final Score", f"{report.final_score:.1%}")
            with col2:
                st.metric("Iterations", report.total_iterations)
            with col3:
                st.metric("Known Failures", len(report.known_failures))

            # Show iteration progression
            if report.scorecards:
                st.subheader("📈 Score Progression")
                scores = {f"Iter {sc.iteration}": sc.score for sc in report.scorecards}
                st.bar_chart(scores)

            # Show known failures
            if report.known_failures:
                st.subheader("❌ Known Failures")
                for f in report.known_failures:
                    st.markdown(f'<div class="warning-box">{f}</div>', unsafe_allow_html=True)

            # Download artifacts
            st.subheader("📥 Download Artifacts")
            report_path = Path(output_dir) / "quality_report.md"
            if report_path.exists():
                st.download_button(
                    "📄 Download Quality Report",
                    report_path.read_text(),
                    "quality_report.md",
                    mime="text/markdown"
                )

            defn_path = Path(output_dir) / "agent_definition.json"
            if defn_path.exists():
                st.download_button(
                    "🤖 Download Agent Definition",
                    defn_path.read_text(),
                    "agent_definition.json",
                    mime="application/json"
                )

        except Exception as e:
            st.error(f"Pipeline error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


def chat_page():
    """Render the Chat with Agent page."""
    st.title("💬 Chat with Generated Agent")
    st.markdown("---")

    # Check if we have a built agent
    if "last_report" not in st.session_state:
        st.info("No agent built yet. Go to '🔨 Build Agent' first, or load an existing definition.")

        # Allow loading existing definition
        st.subheader("📂 Load Existing Agent")
        defn_file = st.file_uploader("Upload agent_definition.json", type=["json"])
        doc_files = st.file_uploader("Upload documents", type=["pdf", "csv", "txt", "md"],
                                     accept_multiple_files=True, key="chat_docs")

        if defn_file and doc_files and st.session_state.get("api_key"):
            if st.button("Load Agent"):
                from forgeai.models import AgentDefinition
                defn_data = json.loads(defn_file.getvalue().decode())
                st.session_state.chat_definition = AgentDefinition(**defn_data)

                doc_dir = tempfile.mkdtemp()
                for f in doc_files:
                    (Path(doc_dir) / f.name).write_bytes(f.getvalue())
                st.session_state.chat_doc_folder = doc_dir
                st.rerun()
        return

    # Get agent info
    if "last_report" in st.session_state:
        definition = st.session_state.last_report.agent_definition
        doc_folder = st.session_state.last_doc_folder
    elif "chat_definition" in st.session_state:
        definition = st.session_state.chat_definition
        doc_folder = st.session_state.chat_doc_folder
    else:
        return

    # Agent info panel
    st.markdown(f"""
    <div class="info-box">
        <h4>🤖 {definition.name}</h4>
        <p>Tools: {', '.join(definition.tools) if definition.tools else 'None'} |
        Retrieval: top_k={definition.retrieval_config.top_k}</p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize chat
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "agent_runner" not in st.session_state:
        try:
            from forgeai.config import ForgeAIConfig, LLMConfig, EmbeddingConfig
            provider = st.session_state.get("llm_provider", "groq")
            config = LLMConfig(
                provider=provider,
                model=st.session_state.get("llm_model", "llama-3.3-70b-versatile"),
                groq_api_key=st.session_state.get("api_key") if provider == "groq" else None,
                google_api_key=st.session_state.get("api_key") if provider == "gemini" else None,
            )
            from forgeai.runners.agent_runner import AgentRunner
            st.session_state.agent_runner = AgentRunner(
                agent_definition=definition,
                llm_config=config,
                embedding_config=EmbeddingConfig(),
                doc_folder=doc_folder,
            )
        except Exception as e:
            st.error(f"Error loading agent: {e}")
            return

    # Display chat history
    for msg in st.session_state.chat_messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-agent">🤖 {msg["content"]}</div>', unsafe_allow_html=True)
            # Source highlighting (stretch goal)
            if "sources" in msg and msg["sources"]:
                with st.expander("📄 View Sources"):
                    for i, src in enumerate(msg["sources"][:3], 1):
                        st.markdown(
                            f'<div class="source-highlight">'
                            f'<strong>Source {i}:</strong> {src[:300]}...</div>',
                            unsafe_allow_html=True
                        )

    # Chat input
    if question := st.chat_input("Ask a question..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": question})

        # Get response
        with st.spinner("Thinking..."):
            answer, chunks = st.session_state.agent_runner.query(question, return_context=True)

        # Add agent response
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": answer,
            "sources": chunks
        })

        st.rerun()

    # Clear chat button
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_messages = []
        if "agent_runner" in st.session_state:
            st.session_state.agent_runner.reset_history()
        st.rerun()


def reports_page():
    """Render the Reports page."""
    st.title("📊 Quality Reports")
    st.markdown("---")

    if "last_report" not in st.session_state:
        st.info("No reports yet. Build an agent first.")
        return

    report = st.session_state.last_report

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Final Score", f"{report.final_score:.1%}")
    with col2:
        st.metric("Iterations", report.total_iterations)
    with col3:
        st.metric("Eval Cases", len(report.eval_set.cases))
    with col4:
        st.metric("Known Failures", len(report.known_failures))

    st.markdown("---")

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Requirements", "🤖 Agent Definition", "📊 Scorecards",
        "🔧 Optimization Log", "❌ Known Failures"
    ])

    with tab1:
        req = report.requirements
        st.json(req.model_dump())

    with tab2:
        st.subheader("System Prompt")
        st.text_area("", report.agent_definition.system_prompt, height=300, disabled=True)
        st.subheader("Configuration")
        st.json({
            "tools": report.agent_definition.tools,
            "retrieval_config": report.agent_definition.retrieval_config.model_dump(),
            "output_contract": report.agent_definition.output_contract.model_dump()
        })

    with tab3:
        for sc in report.scorecards:
            with st.expander(f"Iteration {sc.iteration} — Score: {sc.score:.1%}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Score", f"{sc.score:.1%}")
                with col2:
                    st.metric("Passed", f"{sc.passed}/{sc.total_cases}")
                with col3:
                    st.metric("Failed", f"{sc.failed}/{sc.total_cases}")

                if sc.failure_breakdown:
                    st.bar_chart(sc.failure_breakdown)

                # Individual case scores
                for cs in sc.case_scores:
                    icon = "✅" if cs.score >= 0.7 else "❌"
                    st.markdown(f"{icon} **{cs.case_id}** ({cs.case_type.value}): {cs.question[:80]}... — Score: {cs.score:.1%}")

    with tab4:
        if report.optimization_logs:
            for log in report.optimization_logs:
                st.markdown(f"**Iteration {log.iteration} — {log.change_type}**")
                st.markdown(f"- {log.description}")
                st.markdown(f"- Score: {log.score_before:.1%} → {log.score_after:.1%}")
                st.markdown("---")
        else:
            st.info("No optimization was needed or performed.")

    with tab5:
        if report.known_failures:
            for f in report.known_failures:
                st.markdown(f'<div class="warning-box">{f}</div>', unsafe_allow_html=True)
        else:
            st.success("No known failures!")

        if report.recommendations:
            st.subheader("💡 Recommendations")
            for rec in report.recommendations:
                st.markdown(f"- {rec}")

    # Tournament results (stretch goal)
    if report.prompt_tournament_results:
        st.markdown("---")
        st.subheader("🏆 Prompt Tournament Results")
        tournament = report.prompt_tournament_results
        for cand in tournament.get("candidates", []):
            st.markdown(f"- **{cand['name']}:** {cand['score']:.1%}")
        if "winner" in tournament:
            st.success(f"🏆 Winner: {tournament['winner']}")


def main():
    """Main application entry point."""
    apply_theme()
    page = sidebar()

    if page == "🏠 Home":
        home_page()
    elif page == "🔨 Build Agent":
        build_page()
    elif page == "💬 Chat with Agent":
        chat_page()
    elif page == "📊 Reports":
        reports_page()


if __name__ == "__main__":
    main()
