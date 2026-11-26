"""Tests for End-to-End Pipeline, Baseline Comparison, and Regression Mode"""

import pytest
import json
from pathlib import Path
from forgeai.config import ForgeAIConfig, LLMConfig
from forgeai.models import RequirementsDocument, AgentDefinition
from forgeai.core.interviewer import IntakeInterviewer
from forgeai.core.agent_generator import AgentGenerator
from forgeai.core.eval_generator import EvalGenerator
from forgeai.core.baseline_comparator import BaselineComparator, HUMAN_BASELINE_HR_AGENT
from forgeai.core.regression_runner import RegressionRunner


def test_intake_and_agent_generator(tmp_path):
    cfg = ForgeAIConfig()
    doc = tmp_path / "policy.txt"
    doc.write_text("Leave policy: 21 days annual leave, 12 days sick leave.")

    interviewer = IntakeInterviewer(cfg.llm, ["current_date", "calculator"])
    reqs = interviewer.build_requirements(
        brief="Assistant for employee leave entitlements.",
        doc_folder=str(tmp_path),
        auto_mode=True
    )
    assert reqs.scope != ""

    generator = AgentGenerator(cfg.llm, ["current_date", "calculator"])
    agent_def = generator.generate(reqs)
    assert agent_def.name != ""
    assert "system_prompt" in agent_def.model_dump()


def test_eval_generator_count(tmp_path):
    cfg = ForgeAIConfig()
    doc_samples = ["Annual leave is 21 days. Sick leave is 12 days.", "Health insurance is covered up to 5,00,000."]
    reqs = RequirementsDocument(
        scope="HR assistant",
        audience="employees",
        tone="professional",
        must_answer_topics=["leave", "benefits"],
        must_refuse_topics=["legal advice"],
        document_summary="HR manual"
    )

    eval_gen = EvalGenerator(cfg.llm)
    eval_set = eval_gen.generate(reqs, doc_samples, num_cases=24)
    assert len(eval_set.cases) >= 20
    assert any(c.should_refuse for c in eval_set.cases)


def test_baseline_and_regression_execution(tmp_path):
    hr_artifacts = Path("forgeai/demos/hr_policy_assistant/artifacts")
    if not hr_artifacts.exists() or not (hr_artifacts / "agent_definition.json").exists():
        pytest.skip("HR artifacts not found")

    factory_def = AgentDefinition(**json.loads((hr_artifacts / "agent_definition.json").read_text()))
    eval_set = json.loads((hr_artifacts / "eval_set.json").read_text())

    from forgeai.models import EvalSet
    eval_set_obj = EvalSet(**eval_set)

    comparator = BaselineComparator()
    comp_res = comparator.compare(
        factory_definition=factory_def,
        human_definition=HUMAN_BASELINE_HR_AGENT,
        eval_set=eval_set_obj,
        doc_folder="forgeai/demos/hr_policy_assistant/documents",
        output_dir=str(tmp_path / "comp")
    )
    assert "factory_score" in comp_res
    assert (tmp_path / "comp" / "factory_vs_human_baseline.md").exists()


def test_unseen_brief_and_documents(tmp_path):
    """Prove ForgeAI works on a brand-new unseen brief and unseen document names."""
    from forgeai.pipeline import ForgeAIPipeline
    from forgeai.config import ForgeAIConfig, LLMConfig, BudgetConfig

    docs_dir = tmp_path / "sec_docs"
    docs_dir.mkdir()
    (docs_dir / "incident_playbook.txt").write_text(
        "SECTION 1: SEVERITY LEVELS\n"
        "P1 Critical Incidents require acknowledgement within 15 minutes and escalation to CISO.\n"
        "P2 High Incidents require acknowledgement within 60 minutes.\n"
        "SECTION 2: PASSWORD ROTATION\n"
        "Service account keys must be rotated every 90 days using Vault.\n"
        "Phishing reports must be forwarded to security-ops@acme-corp.example within 1 hour.\n",
        encoding="utf-8",
    )
    (docs_dir / "access_control_matrix.csv").write_text(
        "role,system,access_level,approval_required\n"
        "Intern,ProductionDB,None,VP Engineering\n"
        "SRE,ProductionDB,ReadWrite,Security Lead\n"
        "Analyst,AnalyticsWarehouse,ReadOnly,Manager\n",
        encoding="utf-8",
    )

    brief = (
        "I need an IT Security and Incident Response assistant for Acme engineering staff. "
        "It should answer questions about incident severity SLAs, password rotation, and role-based access "
        "from the access control matrix CSV. It must refuse to grant production access or provide legal advice."
    )
    out_dir = tmp_path / "unseen_out"

    cfg = ForgeAIConfig(
        llm=LLMConfig(provider="simulator"),
        budget=BudgetConfig(max_iterations=1),
        verbose=False,
    )
    pipeline = ForgeAIPipeline(cfg)
    report = pipeline.run(
        brief=brief,
        doc_folder=str(docs_dir),
        output_dir=str(out_dir),
        auto_mode=True,
        run_tournament=False,
    )

    assert len(report.eval_set.cases) >= 20
    assert "weather_api" not in report.agent_definition.tools
    assert "csv_lookup" in report.agent_definition.tools
    assert "incident_playbook.txt" in report.agent_definition.document_list
    assert "access_control_matrix.csv" in report.agent_definition.document_list
    assert (out_dir / "quality_report.md").exists()
    assert (out_dir / "judge_results.json").exists()
    assert (out_dir / "raw_responses.json").exists()
    assert (out_dir / "system_prompt.txt").exists()
    assert (out_dir / "eval_generation_prompt.txt").exists()
