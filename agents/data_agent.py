import os
import sys
from dotenv import load_dotenv

from google.adk import Agent
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
env_path = os.path.join(project_root, ".env")
load_dotenv(env_path)

server_path = os.path.join(project_root, "mcp_server", "server.py")

fastmcp_path = "fastmcp"
if os.name == "nt":
    local_path = os.path.join(project_root, "venv", "Scripts", "fastmcp.exe")
    if os.path.exists(local_path):
        fastmcp_path = local_path

server_params = StdioServerParameters(
    command=fastmcp_path,
    args=["run", "--no-banner", f"{server_path}:mcp"]
)

connection_params = StdioConnectionParams(server_params=server_params)
mcp_toolset = MCPToolset(connection_params=connection_params)

data_agent = Agent(
    name="data_agent",
    model="gemini-2.5-flash",
    instruction="""You are a data retrieval agent. Your job is to use the available tools to answer questions about expenses, departments, categories, and spending statistics.
You have access to tools from a local MCP server: get_schema, get_expenses, and get_summary_stats.
CRITICAL INSTRUCTION: You must never make up numbers. Only report exactly what the tools return. Your job at this stage is ONLY to retrieve and report data accurately, not to analyze for fraud yet.""",
    tools=[mcp_toolset]
)
