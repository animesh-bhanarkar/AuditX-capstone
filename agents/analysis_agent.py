"""
agents/analysis_agent.py

ADK agent that runs deterministic fraud detection via a FunctionTool
that internally loads the expense CSV and runs all detectors.

Architecture:
  run_fraud_analysis() FunctionTool loads data/expenses.csv internally,
  runs the four detectors, and returns compact findings JSON.
  This avoids piping 216 KB of raw rows through the LLM context.

  MCPToolset kept for supplementary schema/stats queries.
"""

import os
import sys
import json
from dotenv import load_dotenv

import pandas as pd

from google.adk import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters

# ── Path setup ───────────────────────────────────────────────────────────────
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

load_dotenv(os.path.join(project_root, ".env"))

sys.path.insert(0, project_root)
from agents.skills.fraud_detection import run_all_detections  # noqa: E402

DATA_PATH = os.path.join(project_root, "data", "expenses.csv")


# ── Combined fetch-and-detect FunctionTool ────────────────────────────────────

def run_fraud_analysis() -> str:
    """
    Load the full expense dataset and run all fraud and anomaly detectors.

    Performs four deterministic analyses:
    1. Structuring: multiple sub-threshold expenses in a short rolling window
    2. Duplicate claims: identical submissions by the same employee
    3. Category spend spikes: monthly spend 2.5x+ above baseline for that group
    4. Statistical outliers: expenses with z-score above 3 for their category

    No arguments required - data is loaded internally from the project dataset.

    Returns:
        JSON string with total_findings count and a findings list.
        Each finding has: type, severity, description, evidence_count, evidence.
    """
    import time
    t0 = time.time()

    def ts(msg):
        print(f"  [+{time.time()-t0:.2f}s] {msg}", flush=True)

    ts("run_fraud_analysis() called")

    if not os.path.exists(DATA_PATH):
        return json.dumps({"error": f"Data file not found: {DATA_PATH}"})

    ts(f"Loading CSV from {DATA_PATH} ...")
    df = pd.read_csv(DATA_PATH)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    ts(f"CSV loaded — {len(df)} rows")

    ts("Running detection functions ...")
    findings = run_all_detections(df)
    ts(f"Detection complete — {len(findings)} findings")

    # Compact evidence to avoid overwhelming response size
    compact_findings = []
    for f in findings:
        evidence_summary = []
        for ev in f.get("evidence", []):
            evidence_summary.append({
                "expense_id": ev.get("expense_id", ""),
                "employee_name": ev.get("employee_name", ""),
                "department": ev.get("department", ""),
                "date": str(ev.get("date", "")),
                "amount": ev.get("amount", 0),
                "vendor": ev.get("vendor", ""),
            })
        compact_findings.append({
            "type": f["type"],
            "severity": f["severity"],
            "description": f["description"],
            "evidence_count": len(evidence_summary),
            "evidence": evidence_summary[:5],  # cap at 5 rows per finding
        })

    result = json.dumps(
        {"total_findings": len(compact_findings), "findings": compact_findings},
        default=str,
        indent=2,
    )
    ts(f"Findings serialised — {len(result)} bytes. Returning to LLM ...")
    return result


fraud_tool = FunctionTool(func=run_fraud_analysis)


# ── MCP Toolset (supplementary queries) ──────────────────────────────────────
server_path = os.path.join(project_root, "mcp_server", "server.py")
fastmcp_path = os.path.join(project_root, "venv", "Scripts", "fastmcp.exe")

server_params = StdioServerParameters(
    command=fastmcp_path,
    args=["run", "--no-banner", f"{server_path}:mcp"],
)

mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(server_params=server_params)
)


# ── Agent definition ──────────────────────────────────────────────────────────
analysis_agent = Agent(
    name="analysis_agent",
    model="gemini-2.5-flash",
    instruction="""You are a financial fraud and compliance analysis agent.

Your workflow MUST follow these exact steps:
1. Call run_fraud_analysis() with no arguments to run all fraud detectors.
2. Summarize ALL findings from the tool output clearly for an auditor.

Rules you must never break:
- NEVER invent findings. Only report what run_fraud_analysis() returns.
- NEVER skip step 1 - you must call the tool before responding.
- Group your summary by severity: HIGH findings first, then MEDIUM, then LOW.
- For each finding, cite: the type, employee name(s), amounts, dates, and
  expense IDs from the evidence field.
- State the total number of findings at the top of your response.
- If evidence_count > 5, note that only the first 5 rows are shown.
""",
    tools=[fraud_tool, mcp_toolset],
)
