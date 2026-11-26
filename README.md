# 🏭 ForgeAI — The Agent That Builds Agents

> An autonomous agent factory that takes a one-paragraph brief and a folder of documents, and produces a working, tested AI agent — complete with system prompt, retrieval configuration, tool selection, auto-generated evaluations, and an honest quality report.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-green.svg)](https://langchain.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-red.svg)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Setup Instructions](#setup-instructions)
- [Usage](#usage)
- [Demo Runs](#demo-runs)
- [Project Structure](#project-structure)
- [Core Requirements Checklist](#core-requirements-checklist)
- [Stretch Goals](#stretch-goals)
- [Design Decisions](#design-decisions)
- [Known Limitations](#known-limitations)

---

## Overview

ForgeAI is not a chatbot — it's **the machine that builds chatbots**. Give it:

1. **A one-paragraph brief** describing the agent you need
2. **A folder of documents** as the knowledge base

And it autonomously:
- 🗣️ **Interviews** you (or auto-answers) to understand requirements
- 🛡️ **Guards** against hallucination by checking document groundability
- 🤖 **Generates** a complete agent with system prompt, tools, and retrieval config
- 📝 **Creates** 20+ evaluation test cases from the documents
- ⚖️ **Judges** the agent using LLM-as-judge + deterministic checks
- 🔄 **Optimizes** through up to 3 critic-fix iterations
- 📊 **Reports** honestly — explaining its 78% is better than claiming 100%
- 🚀 **Ships** a runnable agent with CLI and web UI

---

## Architecture

```
                        ┌─────────────────────────────────────┐
                        │           ForgeAI Pipeline           │
                        └───────────────┬─────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
        ▼                               ▼                               ▼
┌───────────────┐              ┌───────────────┐              ┌───────────────┐
│  1. INTAKE    │              │  2. GROUND-   │              │  3. AGENT     │
│  INTERVIEWER  │──────────────▶  ABILITY      │──────────────▶  GENERATOR    │
│               │              │  GUARD        │              │               │
│ • Read brief  │              │ • Check docs  │              │ • Sys prompt  │
│ • Ask ≤5 Qs   │              │ • Flag gaps   │              │ • RAG config  │
│ • Struct reqs  │              │ • Warn user   │              │ • Tool select │
└───────────────┘              └───────────────┘              └───────┬───────┘
                                                                      │
        ┌─────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────┐              ┌───────────────┐              ┌───────────────┐
│  4. EVAL      │              │  5. JUDGE     │              │  6. CRITIC-   │
│  GENERATOR    │──────────────▶  (LLM + Det.) │──────────────▶  OPTIMIZER    │
│               │              │               │              │  LOOP (×3)    │
│ • 20+ cases   │              │ • Grounding   │              │               │
│ • Answerable  │              │ • Accuracy    │              │ • Classify    │
│ • OOS/Edge    │              │ • Refusal     │              │ • Fix target  │
│ • Multi-doc   │              │ • Bias defense│              │ • Re-evaluate │
└───────────────┘              └───────────────┘              └───────┬───────┘
                                                                      │
        ┌─────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────┐              ┌───────────────┐              ┌───────────────┐
│  7. HONEST    │              │  8. RUNNABLE  │              │  9. DEMO      │
│  REPORT       │──────────────▶  PRODUCT      │──────────────▶  RUNS         │
│               │              │               │              │               │
│ • Scorecards  │              │ • CLI chat    │              │ • HR policy   │
│ • What fails  │              │ • Streamlit   │              │ • Ship spares │
│ • Why it fails│              │ • Load any def│              │ • Full logs   │
└───────────────┘              └───────────────┘              └───────────────┘
```

### Component Diagram

```
forgeai/
├── config.py           ← LLM provider factory (Groq/Gemini), embeddings, budget
├── models.py           ← Pydantic data models for the entire pipeline
├── pipeline.py         ← Master orchestrator tying all 9 requirements together
│
├── core/
│   ├── document_processor.py  ← PDF/CSV/TXT loading, chunking, FAISS indexing
│   ├── interviewer.py         ← Intake interview + groundability guard
│   ├── agent_generator.py     ← Agent definition generation + prompt tournament
│   ├── eval_generator.py      ← Auto-generate 20+ test cases from documents
│   ├── judge.py               ← LLM-as-judge + deterministic scoring
│   └── optimizer.py           ← Critic analysis + targeted fix prescription
│
├── tools/
│   └── registry.py     ← 4 tools: csv_lookup, calculator, weather_api, current_date
│
├── runners/
│   ├── agent_runner.py  ← Generic RAG runner for any agent definition
│   └── cli_runner.py    ← Interactive CLI chat interface
│
├── ui/
│   └── streamlit_app.py ← Full Streamlit web UI (factory + chat + reports)
│
└── utils/
    └── report_generator.py ← Honest quality report generation
```

---

## Features

### Core Requirements (All 9 Implemented)

| # | Requirement | Implementation |
|---|-------------|---------------|
| 1 | **Intake Interviewer** | Generates ≤5 clarifying questions, produces structured requirements |
| 2 | **Groundability Guard** | Compares brief against documents, flags unsupported requests |
| 3 | **Agent Generator** | Produces system prompt, retrieval config, tool selection, output contract |
| 4 | **Eval Generator** | Auto-creates 20+ cases: answerable, OOS, edge, multi-doc |
| 5 | **Judge** | LLM-as-judge + deterministic checks with bias defenses |
| 6 | **Critic-Optimizer** | Classify failures → targeted fixes → re-run (max 3 iterations) |
| 7 | **Honest Reporting** | States what fails and why — never claims false 100% |
| 8 | **Runnable Product** | CLI chat + Streamlit UI load any agent definition |
| 9 | **Two Demo Runs** | HR Policy + Ship Spares with complete artifact logs |

### Stretch Goals (All 6 Fully Implemented & Tested)

| Goal | Status | Implementation |
|------|--------|---------------|
| 🏆 **Prompt Tournament** | ✅ | Generates 3 prompt variants (structured, conversational, minimal), evaluates each, selects winner |
| 💰 **Budget Enforcement** | ✅ | Token tracking & latency budget with early stopping when iteration improvement < 2% |
| 🧑 **Human Checkpoint** | ✅ | Interactive pause for human review and approval of the requirements document |
| 👤 **Factory vs Human Baseline** | ✅ | Evaluates hand-crafted agent vs. ForgeAI on 24 test cases; generates comparative scorecard |
| 🔄 **Regression Mode** | ✅ | Evaluates impact of document modifications against historical test suites; pinpoints regressions |
| 🌐 **UI & Hosting** | ✅ | Production-grade Streamlit Web UI with dark/light mode, source citation viewers, and full analytics |

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- A free API key from [Groq](https://console.groq.com) or [Google AI Studio](https://aistudio.google.com/apikey)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/forgeai.git
cd forgeai

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API key
```

### Environment Configuration

```env
# Choose provider: groq or gemini
LLM_PROVIDER=groq

# API Keys (get free from links above)
GROQ_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here

# Model (Groq recommended for free tier)
LLM_MODEL=llama-3.3-70b-versatile
```

---

## Usage

### Run Demo (Quickest Way to See ForgeAI in Action)

```bash
# Run HR Policy Assistant demo
python main.py --demo hr

# Run Ship Spares Procurement demo
python main.py --demo spares

# Run both demos (produces complete artifacts)
python run_demos.py
```

### Build a Custom Agent

```bash
# With inline brief
python main.py --brief "I need an assistant that helps with..." --docs ./my_documents

# With brief file
python main.py --brief-file my_brief.txt --docs ./my_documents --output ./my_output

# Interactive mode (answers questions manually)
python main.py --brief-file brief.txt --docs ./docs --interactive

# With human checkpoint
python main.py --brief-file brief.txt --docs ./docs --human-checkpoint --interactive
```

### Chat with a Generated Agent

```bash
# After running the pipeline, chat with the produced agent
python main.py --chat output/agent_definition.json --docs ./documents
```

### Run Stretch Goals

```bash
# 1. Factory vs Human Baseline comparison
python main.py --baseline forgeai/demos/hr_policy_assistant/artifacts/agent_definition.json \
               --docs forgeai/demos/hr_policy_assistant/documents

# 2. Document Regression Mode
python main.py --regression forgeai/demos/hr_policy_assistant/artifacts/agent_definition.json \
               --docs forgeai/demos/hr_policy_assistant/documents

# 3. Run full automated test suite
pytest tests/ -v
```

### Launch Web UI

```bash
# Start Streamlit interface
streamlit run forgeai/ui/streamlit_app.py

# Or via main.py
python main.py --ui
```

---

## Demo Runs

### Demo 1: HR Policy Assistant 📋

**Brief:** "I need an assistant that answers HR policy questions for OceanWave Maritime shore staff..."

**Documents:**
- `hr_policy_manual.txt` — Complete HR policy (leave, benefits, conduct, grievances, safety)
- `employee_handbook_supplement.txt` — Work schedules, performance management, compensation

**Expected Behavior:**
- ✅ Answers questions about leave policies, benefits, code of conduct
- ✅ Cites specific sections and policy numbers
- ❌ Refuses legal advice, policy exception requests

**Artifacts:** `forgeai/demos/hr_policy_assistant/artifacts/`

---

### Demo 2: Ship Spares Procurement Assistant ⚓

**Brief:** "I need a procurement assistant for OceanWave Maritime's ship spares department..."

**Documents:**
- `ship_spares_catalogue.csv` — 30 marine parts with pricing, suppliers, certifications
- `procurement_guidelines.txt` — Ordering procedures, inventory management, compliance
- `supplier_directory.txt` — 10 approved suppliers with ratings and contact info

**Expected Behavior:**
- ✅ Looks up parts from CSV catalogue
- ✅ Provides supplier information and procurement procedures
- ✅ Performs cost calculations
- ❌ Refuses to approve POs or make vendor commitments

**Artifacts:** `forgeai/demos/ship_spares_assistant/artifacts/`

---

## Project Structure

```
oceanAI/
├── main.py                          # CLI entry point
├── run_demos.py                     # Run both demos end-to-end
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment template
├── .gitignore
├── README.md                        # This file
│
├── forgeai/                         # Main package
│   ├── __init__.py
│   ├── config.py                    # Configuration & LLM factory
│   ├── models.py                    # Pydantic data models
│   ├── pipeline.py                  # Master pipeline orchestrator
│   │
│   ├── core/                        # Core pipeline components
│   │   ├── document_processor.py    # Document loading & chunking
│   │   ├── interviewer.py           # Intake interview & groundability
│   │   ├── agent_generator.py       # Agent definition generation
│   │   ├── eval_generator.py        # Test case generation
│   │   ├── judge.py                 # LLM + deterministic scoring
│   │   └── optimizer.py             # Critic-optimizer loop
│   │
│   ├── tools/                       # Tool registry
│   │   └── registry.py              # csv_lookup, calculator, weather, date
│   │
│   ├── runners/                     # Agent runners
│   │   ├── agent_runner.py          # Generic RAG runner
│   │   └── cli_runner.py            # CLI chat interface
│   │
│   ├── ui/                          # Web interface
│   │   └── streamlit_app.py         # Streamlit app (factory + chat + reports)
│   │
│   ├── utils/                       # Utilities
│   │   └── report_generator.py      # Quality report generation
│   │
│   └── demos/                       # Demo runs with full artifacts
│       ├── hr_policy_assistant/
│       │   ├── brief.txt            # Agent brief
│       │   ├── documents/           # HR policy documents
│       │   └── artifacts/           # Generated artifacts (after run)
│       │
│       └── ship_spares_assistant/
│           ├── brief.txt            # Agent brief
│           ├── documents/           # Procurement documents + CSV
│           └── artifacts/           # Generated artifacts (after run)
│
└── tests/                           # Test suite
```

---

## Core Requirements Checklist

- [x] **1. Intake Interviewer** — `forgeai/core/interviewer.py`
  - Reads brief, inspects documents, asks ≤5 clarifying questions
  - Produces structured requirements (scope, audience, tone, topics)
  
- [x] **2. Groundability Guard** — `forgeai/core/interviewer.py`
  - Compares brief against document content
  - Flags unsupported topics as warnings
  
- [x] **3. Agent Generator** — `forgeai/core/agent_generator.py`
  - Generates system prompt, retrieval config, tool selection, output contract
  - Only attaches tools the brief needs (HR agent ≠ weather tool)
  
- [x] **4. Eval Generator** — `forgeai/core/eval_generator.py`
  - Auto-generates 20+ test cases from documents
  - Covers: answerable, out-of-scope, edge cases, multi-document
  - Generation prompts committed (not hand-written)
  
- [x] **5. Judge** — `forgeai/core/judge.py`
  - LLM-as-judge for nuanced assessment
  - Deterministic checks for clear-cut cases (refusals, fact matching)
  - Bias defenses: position, self-preference, verbosity
  
- [x] **6. Critic-Optimizer Loop** — `forgeai/core/optimizer.py`
  - Classifies failures: retrieval_miss / prompt_defect / hallucination / wrong_refusal
  - Prescribes targeted fixes, not full regeneration
  - Max 3 iterations, every change logged
  
- [x] **7. Honest Reporting** — `forgeai/utils/report_generator.py`
  - Per-iteration scorecards
  - States what still fails and why
  - Recommendations for improvement
  
- [x] **8. Runnable Product** — `forgeai/runners/`
  - CLI chat runner loads any agent definition
  - Streamlit UI for interactive chat
  
- [x] **9. Two Demo Runs** — `forgeai/demos/`
  - HR Policy Assistant (text documents)
  - Ship Spares Procurement (CSV + text)
  - Complete artifacts committed

---

## Stretch Goals

### 🏆 Prompt Tournament
Generates 3 system prompt variants (structured, conversational, minimal), evaluates each against the eval set, and selects the winner. Results included in the final report.

### 💰 Budget Enforcement
Configurable token budget per run with early stopping when improvement falls below 2% threshold. Prevents wasteful iterations.

### 🧑 Human Checkpoint
Optional pause after requirements generation for human review and approval before agent generation proceeds.

### 🌐 UI & Hosting
Full Streamlit web application with:
- Build Agent page (upload docs, enter brief, configure)
- Chat interface with source highlighting
- Reports dashboard with scorecards and optimization logs
- Dark/light theme toggle

---

## Design Decisions

### Why Groq + Llama 3.3?
- **Free tier** with generous rate limits
- **Fast inference** for iterative pipeline
- Llama 3.3 70B provides strong instruction following
- Easily swappable to Gemini via config

### Why FAISS over ChromaDB?
- Zero infrastructure — no server needed
- Fast for small-medium document collections
- Well-supported in LangChain ecosystem

### Why Deterministic + LLM Judge?
LLM-as-judge alone is unreliable. Deterministic checks catch clear failures (wrong refusals, missing facts) that LLMs might miss or score inconsistently. The combined approach is more trustworthy.

### Why Targeted Fixes over Full Regeneration?
Full regeneration might fix one thing and break another. Targeted fixes are more predictable, produce smaller diffs, and their impact is measurable — exactly what a good engineer does.

---

## Known Limitations

1. **Free-tier rate limits** may cause delays with Groq during optimization loops
2. **Embedding model** (all-MiniLM-L6-v2) is English-only and runs locally
3. **Tool invocation** in generated agents uses keyword matching (production would use function calling)
4. **Eval quality** depends on LLM quality — small models may produce less diverse test cases
5. **No persistence** — vector stores are rebuilt on each run (production would cache)

---

## Document Synthesis Prompts

The demo documents were synthesized using the following prompts:

**HR Policy Manual:**
> "Create a realistic, detailed HR policy manual for a maritime services company called OceanWave Maritime Services. Include sections on: leave policies (annual, sick, maternity/paternity, bereavement), employee benefits (health insurance, retirement, education), code of conduct (professional standards, anti-harassment, confidentiality), grievance procedures (informal, formal, committee), and workplace safety. Use realistic policy numbers and specific details."

**Ship Spares Catalogue:**
> "Create a CSV catalogue of 30 marine ship spare parts with columns: Part Number, Part Name, Category, Unit Price (USD), Stock Quantity, Minimum Order, Lead Time (Days), Supplier, Supplier Country, Weight (kg), Certification. Include realistic maritime parts across categories: engine, propulsion, navigation, safety, environmental, deck."

**Procurement Guidelines:**
> "Create detailed procurement guidelines for a maritime company including: procurement authority levels, ordering procedures (standard, emergency, blanket), inventory management (stock levels, warehouse ops), supplier management (ASL, performance metrics), and compliance documentation requirements."

---

## Author

**Rhythm Gupta**  
OceanAI Jr. GenAI Engineer — Campus Recruitment Assignment

---

## License

MIT License — see [LICENSE](LICENSE) for details.
