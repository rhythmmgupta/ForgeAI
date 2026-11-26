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
