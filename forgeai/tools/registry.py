"""
Tool Registry
==============
Provides 3-4 tools the factory can choose from when building agents.
The factory must attach ONLY the tools the brief actually needs.

Available tools:
1. csv_lookup - Search and filter CSV data
2. calculator - Perform arithmetic calculations
3. weather_api - Get weather data (open-meteo, keyless)
4. current_date - Get current date and time
"""

import csv
import math
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class ToolRegistry:
    """
    Registry of tools available to generated agents.
    The Agent Generator selects which tools to attach based on the brief.
    """

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {
            "csv_lookup": {
                "name": "csv_lookup",
                "description": (
                    "Search and filter CSV data files. Useful for looking up "
                    "products, inventory, supplier info, or any tabular data."
                ),
                "function": self.csv_lookup,
                "use_cases": ["procurement", "inventory", "products", "data lookup", "catalogue", "suppliers"]
            },
            "calculator": {
                "name": "calculator",
                "description": (
                    "Perform arithmetic calculations. Useful for computing "
                    "totals, percentages, unit conversions, and cost estimates."
                ),
                "function": self.calculator,
                "use_cases": ["calculations", "math", "costs", "pricing", "budgets", "conversions"]
            },
            "weather_api": {
                "name": "weather_api",
                "description": (
                    "Get current weather data for any location using the "
                    "Open-Meteo API (no API key required)."
                ),
                "function": self.weather_api,
                "use_cases": ["weather", "temperature", "climate", "meteorology", "maritime weather"]
            },
            "current_date": {
                "name": "current_date",
                "description": (
                    "Get the current date and time. Useful for time-sensitive "
                    "queries about deadlines, schedules, and validity periods."
                ),
                "function": self.current_date,
                "use_cases": ["date", "time", "deadline", "schedule", "validity", "calendar"]
            }
        }

    @property
    def available_tools(self) -> List[str]:
        """Return list of all tool names."""
        return list(self._tools.keys())

    def get_tool_descriptions(self) -> str:
        """Get formatted descriptions of all tools."""
        lines = []
        for name, tool in self._tools.items():
            lines.append(f"- **{name}**: {tool['description']}")
        return "\n".join(lines)

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a tool by name."""
        return self._tools.get(name)

    def execute_tool(self, name: str, **kwargs) -> str:
        """Execute a tool by name with given arguments."""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found in registry."
        try:
            return tool["function"](**kwargs)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

    # ─── Tool Implementations ────────────────────────────────────────────

    @staticmethod
    def csv_lookup(
        file_path: str = "",
        query: str = "",
        column: str = "",
        value: str = ""
    ) -> str:
        """
        Search a CSV file for matching rows.
        
        Args:
            file_path: Path to the CSV file
            query: Free-text search across all columns
            column: Specific column to filter
            value: Value to match in the column
        """
        path = Path(file_path)
        if not path.exists():
            return f"CSV file not found: {file_path}"

        results = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if column and value:
                        # Filter by specific column
                        if column in row and value.lower() in str(row[column]).lower():
                            results.append(dict(row))
                    elif query:
                        # Free text search across all columns
                        row_text = " ".join(str(v) for v in row.values()).lower()
                        if query.lower() in row_text:
                            results.append(dict(row))

            if not results:
                return "No matching records found."

            # Format results
            output_lines = [f"Found {len(results)} matching record(s):\n"]
            for i, r in enumerate(results[:20], 1):  # Limit to 20 results
                output_lines.append(f"Record {i}:")
                for k, v in r.items():
                    output_lines.append(f"  {k}: {v}")
                output_lines.append("")

            return "\n".join(output_lines)
        except Exception as e:
            return f"Error reading CSV: {str(e)}"

    @staticmethod
    def calculator(expression: str = "") -> str:
        """
        Evaluate a mathematical expression safely.
        
        Args:
            expression: Mathematical expression to evaluate (e.g., "15 * 24 + 100")
        """
        if not expression:
            return "No expression provided."

        # Safe math evaluation
        allowed_names = {
            "abs": abs, "round": round, "min": min, "max": max,
            "sum": sum, "pow": pow,
            "sqrt": math.sqrt, "ceil": math.ceil, "floor": math.floor,
            "log": math.log, "log10": math.log10,
            "pi": math.pi, "e": math.e,
        }

        try:
            # Remove potentially dangerous content
            sanitized = expression.strip()
            for forbidden in ["import", "exec", "eval", "open", "__", "os.", "sys."]:
                if forbidden in sanitized.lower():
                    return f"Error: Expression contains forbidden term '{forbidden}'"

            result = eval(sanitized, {"__builtins__": {}}, allowed_names)
            return f"Result: {result}"
        except Exception as e:
            return f"Error evaluating expression: {str(e)}"

    @staticmethod
    def weather_api(latitude: float = 0.0, longitude: float = 0.0, location: str = "") -> str:
        """
        Get current weather data using Open-Meteo API.
        Note: Requires network access. Returns mock data if API unavailable.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            location: Location name (for display only)
        """
        try:
            import urllib.request
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={latitude}&longitude={longitude}"
                f"&current_weather=true"
            )
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                weather = data.get("current_weather", {})
                loc = location or f"({latitude}, {longitude})"
                return (
                    f"Weather for {loc}:\n"
                    f"  Temperature: {weather.get('temperature', 'N/A')}°C\n"
                    f"  Wind Speed: {weather.get('windspeed', 'N/A')} km/h\n"
                    f"  Wind Direction: {weather.get('winddirection', 'N/A')}°\n"
                    f"  Weather Code: {weather.get('weathercode', 'N/A')}"
                )
        except Exception as e:
            # Return mock data if API is unavailable
            return (
                f"Weather for {location or 'requested location'} "
                f"(simulated - API unavailable): "
                f"Temperature: 22°C, Wind: 15 km/h, Conditions: Clear"
            )

    @staticmethod
    def current_date() -> str:
        """Get the current date and time."""
        now = datetime.now()
        return (
            f"Current Date and Time:\n"
            f"  Date: {now.strftime('%Y-%m-%d')}\n"
            f"  Time: {now.strftime('%H:%M:%S')}\n"
            f"  Day: {now.strftime('%A')}\n"
            f"  Timezone: Local"
        )
