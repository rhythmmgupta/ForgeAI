"""
ForgeAI Streamlit UI — Production Grade
=======================================
A modern, intuitive web dashboard for the ForgeAI agent factory,
chat runner, and evaluation analytics.
"""

import sys
from pathlib import Path

# Ensure project root is always in sys.path regardless of how Streamlit is invoked
_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import os
import json
import tempfile
import shutil

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="ForgeAI — Autonomous Agent Factory",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)


def apply_theme():
    """Apply modern responsive theme styling with crystal-clear contrast in both Light and Dark modes."""
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = True

    if st.session_state.dark_mode:
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
        .stApp { background-color: #0b0f19 !important; color: #f1f5f9 !important; }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #111827 !important;
            border-right: 1px solid #1f2937 !important;
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #f8fafc !important;
        }
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
            color: #cbd5e1 !important;
        }

        /* Radio buttons in sidebar */
        div[data-testid="stRadio"] label {
            padding: 6px 12px !important;
            border-radius: 8px !important;
            transition: all 0.15s ease !important;
        }
        div[data-testid="stRadio"] label p,
        div[data-testid="stRadio"] label div,
        div[data-testid="stRadio"] label span,
        div[role="radiogroup"] label p {
            color: #f1f5f9 !important;
            font-size: 15px !important;
            font-weight: 500 !important;
        }
        div[data-testid="stRadio"] label:hover {
            background: rgba(56, 189, 248, 0.1) !important;
        }

        /* Widget Labels */
        [data-testid="stWidgetLabel"] label p,
        [data-testid="stWidgetLabel"] p {
            color: #e2e8f0 !important;
            font-weight: 600 !important;
        }

        /* Headings and body text */
        h1, h2, h3, h4, h5, h6 {
            color: #f8fafc !important;
        }
        p, li {
            color: #cbd5e1;
        }
        
        /* Modern Cards */
        .glass-card {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95)) !important;
            border: 1px solid rgba(75, 85, 99, 0.5) !important;
            border-radius: 12px;
            padding: 22px;
            margin-bottom: 18px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            color: #f8fafc !important;
        }
        .glass-card h4, .glass-card h3, .glass-card strong {
            color: #f8fafc !important;
        }
        .glass-card p {
            color: #cbd5e1 !important;
            margin-bottom: 8px;
        }
        
        .metric-card {
            background: #1e293b !important;
            border: 1px solid #334155 !important;
            border-radius: 10px;
            padding: 16px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.25);
        }
        
        .metric-title { font-size: 0.85em; color: #94a3b8 !important; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
        .metric-value { font-size: 1.8em; font-weight: 700; color: #38bdf8 !important; margin: 4px 0; }
        .metric-subtitle { font-size: 0.8em; color: #94a3b8 !important; }
        
        /* Badges */
        .badge-chip {
            display: inline-block;
            background: #0284c7;
            color: white !important;
            padding: 3px 10px;
            border-radius: 9999px;
            font-size: 0.78em;
            font-weight: 600;
            margin-right: 6px;
        }
        
        .badge-warning {
            background: #451a03 !important;
            color: #fde68a !important;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.88em;
            margin-bottom: 8px;
            border-left: 4px solid #f59e0b;
        }

        .badge-success {
            background: #064e3b !important;
            color: #a7f3d0 !important;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.88em;
            margin-bottom: 8px;
            border-left: 4px solid #10b981;
        }
        
        /* Chat bubbles */
        .chat-user {
            background: #1d4ed8 !important;
            color: #eff6ff !important;
            padding: 14px 18px;
            border-radius: 16px 16px 4px 16px;
            margin: 10px 0;
            max-width: 80%;
            margin-left: auto;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            line-height: 1.5;
            font-size: 0.95em;
        }
        
        .chat-agent {
            background: #1e293b !important;
            color: #f8fafc !important;
            padding: 14px 18px;
            border-radius: 16px 16px 16px 4px;
            margin: 10px 0;
            max-width: 85%;
            border: 1px solid #334155 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            line-height: 1.5;
            font-size: 0.95em;
        }
        
        .source-highlight {
            background: #0f172a !important;
            border-left: 4px solid #38bdf8 !important;
            padding: 10px 14px;
            border-radius: 6px;
            margin: 6px 0;
            font-size: 0.88em;
            color: #cbd5e1 !important;
        }
        
        /* Buttons */
        .stButton button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
        .stApp { background-color: #f8fafc !important; color: #0f172a !important; }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #ffffff !important;
            border-right: 1px solid #e2e8f0 !important;
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #0f172a !important;
        }
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
            color: #334155 !important;
        }

        /* Radio buttons in sidebar */
        div[data-testid="stRadio"] label {
            padding: 6px 12px !important;
            border-radius: 8px !important;
            transition: all 0.15s ease !important;
        }
        div[data-testid="stRadio"] label p,
        div[data-testid="stRadio"] label div,
        div[data-testid="stRadio"] label span,
        div[role="radiogroup"] label p {
            color: #0f172a !important;
            font-size: 15px !important;
            font-weight: 600 !important;
        }
        div[data-testid="stRadio"] label:hover {
            background: rgba(2, 132, 199, 0.08) !important;
        }

        /* Widget Labels */
        [data-testid="stWidgetLabel"] label p,
        [data-testid="stWidgetLabel"] p {
            color: #0f172a !important;
            font-weight: 600 !important;
        }

        /* Headings and body text */
        h1, h2, h3, h4, h5, h6 {
            color: #0f172a !important;
        }
        p, li {
            color: #1e293b;
        }
        
        .glass-card {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 12px;
            padding: 22px;
            margin-bottom: 18px;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
            color: #0f172a !important;
        }
        .glass-card h4, .glass-card h3, .glass-card strong {
            color: #0f172a !important;
        }
        .glass-card p {
            color: #334155 !important;
            margin-bottom: 8px;
        }
        
        .metric-card {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 10px;
            padding: 16px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
        }
        
        .metric-title { font-size: 0.85em; color: #475569 !important; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
        .metric-value { font-size: 1.8em; font-weight: 700; color: #0284c7 !important; margin: 4px 0; }
        .metric-subtitle { font-size: 0.8em; color: #64748b !important; }
        
        .badge-chip {
            display: inline-block;
            background: #0284c7;
            color: white !important;
            padding: 3px 10px;
            border-radius: 9999px;
            font-size: 0.78em;
            font-weight: 600;
            margin-right: 6px;
        }
        
        .badge-warning {
            background: #fef3c7 !important;
            color: #92400e !important;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.88em;
            margin-bottom: 8px;
            border-left: 4px solid #f59e0b;
        }

        .badge-success {
            background: #d1fae5 !important;
            color: #065f46 !important;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.88em;
            margin-bottom: 8px;
            border-left: 4px solid #10b981;
        }
        
        .chat-user {
            background: #0284c7 !important;
            color: #ffffff !important;
            padding: 14px 18px;
            border-radius: 16px 16px 4px 16px;
            margin: 10px 0;
            max-width: 80%;
            margin-left: auto;
            box-shadow: 0 2px 8px rgba(2, 132, 199, 0.15);
            line-height: 1.5;
            font-size: 0.95em;
        }
        
        .chat-agent {
            background: #ffffff !important;
            color: #0f172a !important;
            padding: 14px 18px;
            border-radius: 16px 16px 16px 4px;
            margin: 10px 0;
            max-width: 85%;
            border: 1px solid #cbd5e1 !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
            line-height: 1.5;
            font-size: 0.95em;
        }
        
        .source-highlight {
            background: #f1f5f9 !important;
            border-left: 4px solid #0284c7 !important;
            padding: 10px 14px;
            border-radius: 6px;
            margin: 6px 0;
            font-size: 0.88em;
            color: #1e293b !important;
        }

        /* Buttons */
        .stButton button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        </style>
        """, unsafe_allow_html=True)


def sidebar():
    """Render sidebar with navigation and settings."""
    with st.sidebar:
        st.markdown("## 🏭 ForgeAI")
        st.caption("Autonomous Agent Factory • OceanAI")
        st.divider()

        # Navigation
        page = st.radio(
            "Select View",
            ["🏠 Overview", "🔨 Build Agent", "💬 Interactive Chat", "📊 Scorecards & Analytics"],
            label_visibility="collapsed"
        )

        st.divider()

        # Execution Mode & LLM Settings
        st.markdown("### ⚙️ Engine Settings")
        
        provider_display = st.selectbox(
            "Inference Engine",
            [
                "⚡ Simulator / Demo Mode (No API Key Required)",
                "Groq (Fast Cloud Inference)",
                "Google Gemini (Google AI Studio)"
            ]
        )
        
        if "Simulator" in provider_display:
            provider = "simulator"
            model = "forgeai-offline-simulator"
            api_key = "simulation_mode"
            st.success("✅ Zero-config mode active. No API key needed for testing.")
        elif "Groq" in provider_display:
            provider = "groq"
            api_key = st.text_input("Groq API Key", type="password", value=os.getenv("GROQ_API_KEY", ""))
            model = st.selectbox("Model", ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"])
        else:
            provider = "gemini"
            api_key = st.text_input("Google AI Key", type="password", value=os.getenv("GOOGLE_API_KEY", ""))
            model = st.selectbox("Model", ["gemini-2.0-flash", "gemini-1.5-flash"])

        st.session_state.llm_provider = provider
        st.session_state.llm_model = model
        st.session_state.api_key = api_key

        st.divider()
        dark_mode = st.toggle("🌙 Dark Mode", value=st.session_state.get("dark_mode", True))
        st.session_state.dark_mode = dark_mode

        return page


def home_page():
    """Render the Overview page."""
    st.markdown("""
    # 🏭 ForgeAI — Autonomous Agent Factory
    > Autonomous Agent Generation, Retrieval Optimization & Rigorous Evaluation Platform
    """)
    st.markdown("---")

    col_hero1, col_hero2 = st.columns([3, 2])
    with col_hero1:
        st.markdown("""
        ### What is ForgeAI?
        ForgeAI is an **autonomous agent factory**. Rather than manually tweaking prompts and tools, 
        admins write a single natural language paragraph and provide a folder of documents.
        
        **ForgeAI autonomously:**
        - 🗣️ **Interviews & Guards**: Clarifies ambiguities and flags unsupported requests before hallucination starts.
        - 🤖 **Drafts Declarative Agents**: Synthesizes system prompts, RAG chunking parameters, and tool attachments.
        - 📝 **Auto-Generates Test Sets**: Synthesizes 20+ grounded test cases across answerable, refusal, and edge cases.
        - ⚖️ **Judges with Bias Defenses**: Blends deterministic verification with LLM-as-judge, defending against verbosity and position bias.
        - 🔄 **Critic-Optimizer Loop**: Diagnoses failures into standard categories and applies targeted fixes (max 3 iterations).
        - 📊 **Honest Reporting**: Explains remaining failure points rather than fabricating suspicious 100% scores.
        """)
    
    with col_hero2:
        st.markdown("""
        <div class="glass-card">
            <h4 style="margin-top:0;">⚡ Enterprise Engine Highlights</h4>
            <p>✅ <strong>Autonomous 6-Stage Factory</strong>: Intake, Agent Synthesis, Eval Generation, Bias-Guarded Judge & Optimizer</p>
            <p>✅ <strong>Production Benchmarks</strong>: Factory vs Human Baseline comparison & Document Regression suites</p>
            <p>✅ <strong>Prompt Tournament</strong>: Multi-candidate generation with head-to-head evaluation</p>
            <p>✅ <strong>Zero-Config Mode</strong>: Built-in resilient simulation LLM for offline demonstration</p>
            <p>✅ <strong>Quality Assurance</strong>: Comprehensive automated test suite passing all verification checks</p>
        </div>
        """, unsafe_allow_html=True)

    # 4 Key Metrics
    st.markdown("### 📊 Architecture at a Glance")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-title">Pipeline Architecture</div>
            <div class="metric-value">6 Stages</div>
            <div class="metric-subtitle">Intake through Optimizer</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-title">Advanced Suites</div>
            <div class="metric-value">Full Suite</div>
            <div class="metric-subtitle">Tournament, Baseline & Regression</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-title">Pre-Trained Systems</div>
            <div class="metric-value">2 Domains</div>
            <div class="metric-subtitle">HR Policy & Maritime Spares</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-title">Tool Registry</div>
            <div class="metric-value">Sandboxed</div>
            <div class="metric-subtitle">Restrained Attachment Model</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🚀 Quick Navigation")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("**🔨 Build an Agent**\n\nSynthesize an agent from scratch or 1-click load pre-configured HR or Spares templates.")
    with c2:
        st.success("**💬 Interactive Chat**\n\nDirectly chat with the pre-built HR Policy or Ship Spares agents with source citations.")
    with c3:
        st.warning("**📊 Reports & Analytics**\n\nInspect scorecards, prompt tournament winner, and Factory vs Human baseline comparisons.")


def build_page():
    """Render the Build Agent page."""
    st.markdown("# 🔨 Build a New Agent")
    st.caption("Transform any paragraph brief and document folder into a tested, runnable AI agent.")
    st.markdown("---")

    # 1-Click Quick-Load Templates
    st.markdown("### ⚡ Quick-Start Templates (1-Click)")
    col_t1, col_t2, col_t3 = st.columns(3)
    
    with col_t1:
        if st.button("📋 Load HR Policy Template", use_container_width=True):
            st.session_state.template_brief = Path("forgeai/demos/hr_policy_assistant/brief.txt").read_text()
            st.session_state.template_name = "hr"
            st.success("Loaded HR Policy brief and documents!")
    with col_t2:
        if st.button("⚓ Load Ship Spares Template", use_container_width=True):
            st.session_state.template_brief = Path("forgeai/demos/ship_spares_assistant/brief.txt").read_text()
            st.session_state.template_name = "spares"
            st.success("Loaded Ship Spares brief and catalogue!")
    with col_t3:
        if st.button("🔄 Clear Form", use_container_width=True):
            st.session_state.template_brief = ""
            st.session_state.template_name = None
            st.rerun()

    # Brief input
    st.markdown("### 📝 Agent Brief")
    default_brief = st.session_state.get("template_brief", "")
    brief = st.text_area(
        "Enter a one-paragraph natural language brief:",
        value=default_brief,
        height=110,
        placeholder="Example: I need an assistant that answers HR policy questions for OceanWave Maritime shore staff..."
    )

    # Document Section
    st.markdown("### 📄 Knowledge Base Documents")
    
    template_name = st.session_state.get("template_name")
    if template_name == "hr":
        st.info("📁 **Pre-loaded Documents from HR Demo:** `hr_policy_manual.txt`, `employee_handbook_supplement.txt`")
        uploaded_files = []
    elif template_name == "spares":
        st.info("📁 **Pre-loaded Documents from Spares Demo:** `ship_spares_catalogue.csv`, `procurement_guidelines.txt`, `supplier_directory.txt`")
        uploaded_files = []
    else:
        uploaded_files = st.file_uploader(
            "Upload knowledge base files (.txt, .pdf, .csv, .md):",
            type=["pdf", "csv", "txt", "md"],
            accept_multiple_files=True
        )

    # Advanced Settings
    with st.expander("⚙️ Advanced Pipeline Configuration"):
        c_adv1, c_adv2 = st.columns(2)
        with c_adv1:
            max_iter = st.slider("Max Optimization Iterations", 1, 3, 2)
            run_tournament = st.checkbox("Run Prompt Tournament (Stretch Goal)", value=True)
        with c_adv2:
            num_cases = st.slider("Evaluation Test Cases", 12, 30, 24)
            auto_mode = st.checkbox("Auto-Answer Intake Questions", value=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Run Factory Button
    if st.button("🚀 Run ForgeAI Factory", type="primary", use_container_width=True):
        if not brief.strip():
            st.error("Please enter a brief or choose a template above.")
            return

        # Determine doc directory
        if template_name == "hr":
            doc_dir = "forgeai/demos/hr_policy_assistant/documents"
        elif template_name == "spares":
            doc_dir = "forgeai/demos/ship_spares_assistant/documents"
        else:
            if not uploaded_files:
                st.error("Please upload at least one document or select a pre-loaded template.")
                return
            doc_dir = tempfile.mkdtemp()
            for f in uploaded_files:
                (Path(doc_dir) / f.name).write_bytes(f.getvalue())

        output_dir = tempfile.mkdtemp()

        # Execute pipeline
        try:
            from forgeai.config import ForgeAIConfig, LLMConfig, BudgetConfig
            from forgeai.pipeline import ForgeAIPipeline

            prov = st.session_state.get("llm_provider", "simulator")
            key = st.session_state.get("api_key", "")
            
            cfg = ForgeAIConfig(
                llm=LLMConfig(
                    provider=prov,
                    model=st.session_state.get("llm_model", "forgeai-offline-simulator"),
                    groq_api_key=key if prov == "groq" else None,
                    google_api_key=key if prov == "gemini" else None,
                ),
                budget=BudgetConfig(max_iterations=max_iter)
            )

            pipeline = ForgeAIPipeline(cfg)

            with st.status("🏭 ForgeAI Factory in Progress...", expanded=True) as status:
                st.write("🗣️ **Stage 1 & 2**: Running Intake Interview & Groundability Guard...")
                st.write("🤖 **Stage 3**: Generating declarative agent & running prompt tournament...")
                st.write("📝 **Stage 4**: Auto-synthesizing evaluation suite from documents...")
                st.write("⚖️ **Stage 5 & 6**: Executing Judge & Critic-Optimizer self-improvement loop...")
                
                report = pipeline.run(
                    brief=brief,
                    doc_folder=doc_dir,
                    output_dir=output_dir,
                    auto_mode=auto_mode,
                    run_tournament=run_tournament
                )
                status.update(label="✅ Agent Factory Successfully Finished!", state="complete")

            st.session_state.last_report = report
            st.session_state.last_doc_folder = doc_dir
            st.session_state.last_output_dir = output_dir

            st.balloons()
            st.success(f"🎉 Agent '{report.agent_definition.name}' produced with Score: {report.final_score:.1%}!")

            # Display Quick Results
            r1, r2, r3, r4 = st.columns(4)
            with r1:
                st.metric("Final Score", f"{report.final_score:.1%}")
            with r2:
                st.metric("Iterations Run", report.total_iterations)
            with r3:
                st.metric("Test Cases", len(report.eval_set.cases))
            with r4:
                st.metric("Known Failures", len(report.known_failures))

            st.info("💡 Navigate to **'💬 Interactive Chat'** to test the agent, or **'📊 Scorecards & Analytics'** for full reports.")

        except Exception as e:
            st.error(f"Error during factory execution: {e}")
            import traceback
            st.code(traceback.format_exc())


def chat_page():
    """Render the Interactive Chat page."""
    st.markdown("# 💬 Interactive Chat Runner")
    st.caption("Interact with any generated agent in real-time with RAG retrieval and source citation highlighting.")
    st.markdown("---")

    # Select agent source
    agent_options = [
        "📋 OceanWave Shore Staff HR Policy Assistant (Pre-built Demo)",
        "⚓ OceanWave Ship Spares Procurement Assistant (Pre-built Demo)"
    ]
    if "last_report" in st.session_state:
        agent_options.insert(0, f"🔨 Currently Built Agent: {st.session_state.last_report.agent_definition.name}")

    selected_agent_choice = st.selectbox("Select Agent to Chat With:", agent_options)

    # Resolve agent definition & doc folder
    if "Currently Built Agent" in selected_agent_choice:
        definition = st.session_state.last_report.agent_definition
        doc_folder = st.session_state.last_doc_folder
    elif "HR Policy" in selected_agent_choice:
        hr_art = Path("forgeai/demos/hr_policy_assistant/artifacts/agent_definition.json")
        from forgeai.models import AgentDefinition
        definition = AgentDefinition(**json.loads(hr_art.read_text(encoding="utf-8")))
        doc_folder = "forgeai/demos/hr_policy_assistant/documents"
    else:
        spares_art = Path("forgeai/demos/ship_spares_assistant/artifacts/agent_definition.json")
        from forgeai.models import AgentDefinition
        definition = AgentDefinition(**json.loads(spares_art.read_text(encoding="utf-8")))
        doc_folder = "forgeai/demos/ship_spares_assistant/documents"

    # Agent summary card
    tool_list = ", ".join(definition.tools) if definition.tools else "None"
    st.markdown(f"""
    <div class="glass-card">
        <h4 style="margin:0 0 8px 0; color:#38bdf8;">🤖 {definition.name}</h4>
        <span class="badge-chip">Tools: {tool_list}</span>
        <span class="badge-chip">top_k: {definition.retrieval_config.top_k}</span>
        <span class="badge-chip">chunk_size: {definition.retrieval_config.chunk_size}</span>
        <span class="badge-chip">format: {definition.output_contract.format}</span>
    </div>
    """, unsafe_allow_html=True)

    # Initialize Runner
    runner_key = f"runner_{definition.name}"
    if runner_key not in st.session_state:
        from forgeai.config import ForgeAIConfig, LLMConfig, EmbeddingConfig
        from forgeai.runners.agent_runner import AgentRunner
        
        prov = st.session_state.get("llm_provider", "simulator")
        key = st.session_state.get("api_key", "")
        cfg = LLMConfig(
            provider=prov,
            model=st.session_state.get("llm_model", "forgeai-offline-simulator"),
            groq_api_key=key if prov == "groq" else None,
            google_api_key=key if prov == "gemini" else None,
        )
        st.session_state[runner_key] = AgentRunner(
            agent_definition=definition,
            llm_config=cfg,
            embedding_config=EmbeddingConfig(),
            doc_folder=doc_folder
        )

    # Chat history state
    msg_key = f"msgs_{definition.name}"
    if msg_key not in st.session_state:
        st.session_state[msg_key] = []

    # Prompt chips for quick testing
    st.markdown("**💡 Quick Test Prompts:**")
    cp1, cp2, cp3, cp4 = st.columns(4)
    quick_prompt = None
    if "HR" in definition.name:
        if cp1.button("🌴 Annual Leave Entitlement"):
            quick_prompt = "How many days of paid annual leave do shore staff receive per year?"
        if cp2.button("👶 Maternity Leave Period"):
            quick_prompt = "What is the maternity leave entitlement for a female employee?"
        if cp3.button("🏥 Health Insurance Limit"):
            quick_prompt = "What is the annual health insurance coverage limit per family?"
        if cp4.button("🚫 Refusal Guard Test"):
            quick_prompt = "Can you grant me an exception for 45 days of unapproved leave?"
    else:
        if cp1.button("🔍 MRN-001 Filter Price"):
            quick_prompt = "What is the unit price and minimum order for MRN-001 Engine Filter?"
        if cp2.button("⚓ Propeller Bearing Supplier"):
            quick_prompt = "Which supplier provides Propeller Shaft Bearing MRN-002 and what certification does it have?"
        if cp3.button("💰 Emergency PO Limit"):
            quick_prompt = "What are the approval thresholds and limits for emergency spare parts orders?"
        if cp4.button("🚫 PO Approval Refusal"):
            quick_prompt = "Can you immediately approve purchase order PO-8899 for $100,000?"

    # Display Chat History
    for m in st.session_state[msg_key]:
        if m["role"] == "user":
            st.markdown(f'<div class="chat-user">🧑 {m["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-agent">🤖 {m["content"]}</div>', unsafe_allow_html=True)
            if "sources" in m and m["sources"]:
                with st.expander("📄 View Retrieved Document Sources"):
                    for idx, src in enumerate(m["sources"][:3], 1):
                        st.markdown(f'<div class="source-highlight"><strong>Chunk {idx}:</strong> {src[:280]}...</div>', unsafe_allow_html=True)

    # Input Box
    user_query = st.chat_input("Ask a question about the policy or parts...") or quick_prompt
    if user_query:
        st.session_state[msg_key].append({"role": "user", "content": user_query})
        with st.spinner("Retrieving knowledge & generating grounded response..."):
            runner = st.session_state[runner_key]
            ans, chunks = runner.query(user_query, return_context=True)
        st.session_state[msg_key].append({"role": "assistant", "content": ans, "sources": chunks})
        st.rerun()

    # Reset chat button
    if st.button("🗑️ Clear Conversation Memory"):
        st.session_state[msg_key] = []
        if runner_key in st.session_state:
            st.session_state[runner_key].reset_history()
        st.rerun()


def reports_page():
    """Render the Reports & Analytics page."""
    st.markdown("# 📊 Scorecards & Quality Reports")
    st.caption("Inspect iteration scorecards, failure classifications, and stretch goal comparisons.")
    st.markdown("---")

    report_source = st.selectbox(
        "Select Report Source:",
        [
            "📋 HR Policy Assistant (Demo Run)",
            "⚓ Ship Spares Procurement Assistant (Demo Run)"
        ] + ([f"🔨 Currently Built: {st.session_state.last_report.agent_definition.name}"] if "last_report" in st.session_state else [])
    )

    if "HR Policy" in report_source:
        art_dir = Path("forgeai/demos/hr_policy_assistant/artifacts")
    elif "Ship Spares" in report_source:
        art_dir = Path("forgeai/demos/ship_spares_assistant/artifacts")
    else:
        art_dir = Path(st.session_state.last_output_dir)

    full_rep_file = art_dir / "full_report.json"
    if not full_rep_file.exists():
        st.warning("Report artifacts not found. Please run the demos first.")
        return

    data = json.loads(full_rep_file.read_text(encoding="utf-8"))

    # Top Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Quality Score</div>
            <div class="metric-value">{data.get('final_score', 0):.1%}</div>
            <div class="metric-subtitle">Honest Evaluation Metric</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Optimization Iterations</div>
            <div class="metric-value">{data.get('total_iterations', 0)}</div>
            <div class="metric-subtitle">Self-Improvement Cycles</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Eval Test Suite</div>
            <div class="metric-value">{len(data.get('eval_set', {}).get('cases', []))}</div>
            <div class="metric-subtitle">Auto-Synthesized Cases</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Diagnosed Gaps</div>
            <div class="metric-value">{len(data.get('known_failures', []))}</div>
            <div class="metric-subtitle">Transparent Failure Accounting</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Scorecards & Iterations",
        "⚔️ Factory vs Human Baseline",
        "🔄 Document Regression",
        "📋 Requirements & Guardrails",
        "🤖 Agent Architecture"
    ])

    with tab1:
        st.markdown("### 📈 Iteration Scorecards")
        for sc in data.get("scorecards", []):
            with st.expander(f"Iteration {sc['iteration']} — Overall Score: {sc['score']:.1%}", expanded=True):
                sc_c1, sc_c2 = st.columns([1, 2])
                with sc_c1:
                    st.metric("Score", f"{sc['score']:.1%}")
                    st.metric("Passed / Total", f"{sc['passed']} / {sc['total_cases']}")
                    st.metric("Failed", sc['failed'])
                with sc_c2:
                    if sc.get("failure_breakdown"):
                        st.markdown("**Failure Taxonomy Breakdown:**")
                        st.bar_chart(sc["failure_breakdown"])
                    else:
                        st.success("No critical failure clusters.")

        if data.get("known_failures"):
            st.markdown("### ❌ Honest Failure Accounting")
            st.info("A factory that claims 100% is suspicious; a factory that explains its failures is hired.")
            for kf in data["known_failures"]:
                st.markdown(f'<div class="badge-warning">{kf}</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown("### ⚔️ Stretch Goal: Factory vs Human Baseline")
        baseline_file = art_dir / "factory_vs_human_baseline.json"
        if baseline_file.exists():
            b_data = json.loads(baseline_file.read_text(encoding="utf-8"))
            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                st.metric("Factory Score", f"{b_data.get('factory_score', 0):.1%}")
            with bc2:
                st.metric("Human Baseline Score", f"{b_data.get('human_score', 0):.1%}")
            with bc3:
                adv = b_data.get('factory_score', 0) - b_data.get('human_score', 0)
                st.metric("Factory Advantage", f"{adv:+.1%}")

            md_file = art_dir / "factory_vs_human_baseline.md"
            if md_file.exists():
                st.markdown(md_file.read_text(encoding="utf-8"))
        else:
            st.info("Run baseline comparison for this agent using `python main.py --baseline <path>`")

    with tab3:
        st.markdown("### 🔄 Stretch Goal: Document Regression Analysis")
        reg_file = art_dir / "regression_report.json"
        if reg_file.exists():
            r_data = json.loads(reg_file.read_text(encoding="utf-8"))
            rc1, rc2 = st.columns(2)
            with rc1:
                st.metric("Post-Update Score", f"{r_data.get('new_score', 0):.1%}")
            with rc2:
                st.metric("Detected Regressions", r_data.get('regressions_count', 0))

            reg_md = art_dir / "regression_report.md"
            if reg_md.exists():
                st.markdown(reg_md.read_text(encoding="utf-8"))
        else:
            st.info("Run document regression test using `python main.py --regression <path>`")

    with tab4:
        st.markdown("### 📋 Intake Requirements Document")
        reqs = data.get("requirements", {})
        st.json(reqs)
        if reqs.get("groundability_warnings"):
            st.markdown("### 🛡️ Groundability Guard Warnings")
            for w in reqs["groundability_warnings"]:
                st.markdown(f'<div class="badge-warning">⚠️ {w}</div>', unsafe_allow_html=True)

    with tab5:
        st.markdown("### 🤖 Produced Agent Definition")
        agent_def = data.get("agent_definition", {})
        st.text_area("Declarative System Prompt", agent_def.get("system_prompt", ""), height=220, disabled=True)
        st.json({
            "retrieval_config": agent_def.get("retrieval_config", {}),
            "tools": agent_def.get("tools", []),
            "output_contract": agent_def.get("output_contract", {})
        })


def main():
    apply_theme()
    page = sidebar()
    
    if "Overview" in page:
        home_page()
    elif "Build" in page:
        build_page()
    elif "Chat" in page:
        chat_page()
    elif "Scorecards" in page:
        reports_page()


if __name__ == "__main__":
    main()
