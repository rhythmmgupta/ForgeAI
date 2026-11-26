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
