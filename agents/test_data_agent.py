import asyncio
import os
import sys
import json

# Ensure the parent directory is in sys.path so we can import agents
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from agents.data_agent import data_agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

async def run_query(query):
    print(f"\n========== Query: {query} ==========\n")
    try:
        runner = Runner(
            app_name="auditx_app",
            agent=data_agent,
            session_service=InMemorySessionService(),
            auto_create_session=True
        )
        message = types.Content(role="user", parts=[types.Part.from_text(text=query)])
        async for event in runner.run_async(user_id="test_user", session_id="test_sess", new_message=message):
            print(f"Event: {event}")
            # Print function calls if any
            if hasattr(event, 'get_function_calls'):
                calls = event.get_function_calls()
                for call in calls:
                    print(f"[Tool Call] {call.name} with args:\n{json.dumps(call.args, indent=2)}")
            
            # Print function responses
            if hasattr(event, 'get_function_responses'):
                responses = event.get_function_responses()
                for resp in responses:
                    print(f"[Tool Response] {resp.name} returned data.")
                    
            # Print agent's text response
            if hasattr(event, 'text'):
                text = event.text
                if text:
                    print(f"[Agent Message]\n{text}\n")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error running query: {e}")

async def main():
    print("Starting test for data_agent...")
    
    query1 = "How many expenses are there in the Marketing department, and what is the total and average amount?"
    await run_query(query1)

    query2 = "Show me all expenses over $2000"
    await run_query(query2)

if __name__ == "__main__":
    asyncio.run(main())
