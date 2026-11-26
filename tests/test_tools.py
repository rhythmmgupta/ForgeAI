"""Tests for ForgeAI Tool Registry (Core Requirement Tools)"""

import pytest
from forgeai.tools.registry import ToolRegistry


def test_registry_has_all_tools():
    registry = ToolRegistry()
    tools = registry.available_tools
    assert "csv_lookup" in tools
    assert "calculator" in tools
    assert "weather_api" in tools
    assert "current_date" in tools


def test_calculator_arithmetic():
    registry = ToolRegistry()
    res = registry.calculator("15 * 40 + 100")
    assert "700" in res


def test_calculator_security_guard():
    registry = ToolRegistry()
    res = registry.calculator("__import__('os').system('ls')")
    assert "Error: Expression contains forbidden term" in res


def test_current_date():
    registry = ToolRegistry()
    res = registry.current_date()
    assert "Current Date and Time:" in res


def test_csv_lookup_functionality(tmp_path):
    csv_file = tmp_path / "parts.csv"
    csv_file.write_text("part_id,name,price\nP01,Engine Filter,45.00\nP02,Shaft Bearing,1250.00\n")
    
    registry = ToolRegistry()
    res = registry.csv_lookup(file_path=str(csv_file), query="Filter")
    assert "Engine Filter" in res
    assert "45.00" in res

    # Non-existent query
    res2 = registry.csv_lookup(file_path=str(csv_file), query="Propeller")
    assert "No matching records found" in res2


def test_langchain_structured_tools_and_autowatch(tmp_path):
    from forgeai.config import LLMConfig, EmbeddingConfig
    from forgeai.models import AgentDefinition
    from forgeai.runners.agent_runner import AgentRunner

    registry = ToolRegistry()
    lc_tools = registry.get_langchain_tools(["calculator", "current_date"])
    assert [t.name for t in lc_tools] == ["calculator", "current_date"]

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "policy.txt").write_text("Initial rule: max PTO is 20 days.", encoding="utf-8")

    runner = AgentRunner(
        agent_definition=AgentDefinition(name="Test", system_prompt="Answer from docs.", tools=[]),
        llm_config=LLMConfig(provider="simulator"),
        embedding_config=EmbeddingConfig(),
        doc_folder=str(docs_dir),
    )
    old_fp = runner._doc_fingerprint

    # Add a new document while runner is alive
    (docs_dir / "new_policy.txt").write_text("Updated rule: travel stipend is USD 75 per day.", encoding="utf-8")
    ans, chunks = runner.query("What is the travel stipend?", return_context=True)
    assert runner._doc_fingerprint != old_fp
    assert any("75" in c for c in chunks)
