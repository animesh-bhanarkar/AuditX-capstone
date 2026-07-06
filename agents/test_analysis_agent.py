"""
agents/test_analysis_agent.py

Run the analysis_agent with a single fraud-analysis query.
Prints all tool calls made and the agent's full response.
"""

import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import asyncio
import json
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from agents.analysis_agent import analysis_agent  # noqa: E402
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types


QUERY = (
    "Analyze this expense data for fraud or compliance risks "
    "and list everything you find."
)


async def run_analysis():
    import time
    t_start = time.time()

    def ts(msg):
        elapsed = time.time() - t_start
        print(f"[{elapsed:6.2f}s] {msg}", flush=True)

    print("=" * 70)
    print("AuditX -- Analysis Agent Test")
    print("=" * 70)
    print(f"\nQuery: {QUERY}\n")
    print("-" * 70)

    ts("Initialising Runner + InMemorySessionService ...")
    runner = Runner(
        app_name="auditx_analysis",
        agent=analysis_agent,
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    ts("Runner ready. Building message ...")

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=QUERY)],
    )

    tool_call_count = 0
    ts("Starting runner.run_async() — waiting for first event ...")

    async for event in runner.run_async(
        user_id="auditor",
        session_id="analysis_sess",
        new_message=message,
    ):
        # Tool calls
        if hasattr(event, "get_function_calls"):
            calls = event.get_function_calls()
            for call in calls:
                tool_call_count += 1
                ts(f"[TOOL CALL #{tool_call_count}] {call.name}")
                args_preview = json.dumps(call.args, indent=2)
                if args_preview and args_preview != "{}":
                    if len(args_preview) > 300:
                        args_preview = args_preview[:300] + "\n  ... (truncated)"
                    print(f"  Args: {args_preview}", flush=True)

        # Tool responses
        if hasattr(event, "get_function_responses"):
            responses = event.get_function_responses()
            for resp in responses:
                ts(f"[TOOL RESPONSE] {resp.name} -> data received. Sending findings to LLM ...")

        # Agent text -- check both event.text and event.content.parts
        text_out = None
        if hasattr(event, "text") and event.text:
            text_out = event.text
        elif hasattr(event, "content") and event.content:
            parts = getattr(event.content, "parts", []) or []
            for part in parts:
                t = getattr(part, "text", None)
                if t and not getattr(part, "function_call", None) and not getattr(part, "function_response", None):
                    text_out = (text_out or "") + t

        if text_out:
            ts("LLM response received.")
            print(f"\n{'=' * 70}")
            print("AGENT RESPONSE:")
            print("=" * 70)
            print(text_out, flush=True)

    print("\n" + "-" * 70)
    ts(f"DONE. Total tool calls: {tool_call_count}")
    print("-" * 70)


if __name__ == "__main__":
    asyncio.run(run_analysis())
