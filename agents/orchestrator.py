"""
agents/orchestrator.py

Main entry point that wires together:
- Data extraction & deterministic detection
- PII masking
- LLM narration (Narrative Agent)
- Hallucination / grounding check
- PII unmasking & report generation
"""

import os
import sys
import json
import asyncio
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from agents.skills.fraud_detection import run_all_detections
from agents.guardrails.pii_guard import mask_dataframe, mask_findings, validate_output_grounding, unmask_text
from agents.narrative_agent import narrative_agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

async def run_full_pipeline(on_step=None):
    msg = "1. Loading dataset..."
    print(msg)
    if on_step: on_step(msg)
    df = pd.read_csv(os.path.join(parent_dir, "data", "expenses.csv"))
    
    msg = "2. Running fraud detection..."
    print(msg)
    if on_step: on_step(msg)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    findings = run_all_detections(df)
    
    msg = "3. Masking dataframe to build PII mapping..."
    print(msg)
    if on_step: on_step(msg)
    _, mapping_dict = mask_dataframe(df)
    
    msg = "4. Masking real names in findings..."
    print(msg)
    if on_step: on_step(msg)
    masked_findings = mask_findings(findings, mapping_dict)
    
    # We serialize the masked findings to JSON to send to the LLM
    findings_json = json.dumps(masked_findings, default=str, indent=2)
    
    msg = "5. Sending masked findings to Narrative Agent..."
    print(msg)
    if on_step: on_step(msg)
    runner = Runner(
        app_name="auditx_narrator",
        agent=narrative_agent,
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    
    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=f"Please write an audit report based on these findings:\n{findings_json}")],
    )
    
    narrative_text = ""
    max_retries = 3
    backoff = [5, 10, 20]
    
    for attempt in range(max_retries + 1):
        try:
            async for event in runner.run_async(
                user_id="orchestrator",
                session_id="audit_sess",
                new_message=message,
            ):
                if hasattr(event, "text") and event.text:
                    narrative_text = event.text
                elif hasattr(event, "content") and event.content:
                    parts = getattr(event.content, "parts", []) or []
                    for part in parts:
                        t = getattr(part, "text", None)
                        if t:
                            narrative_text = (narrative_text or "") + t
            break  # Success, exit retry loop
        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "500" in error_str or "429" in error_str or "unavailable" in error_str.lower():
                if attempt < max_retries:
                    wait_time = backoff[attempt]
                    if on_step:
                        on_step(f"AI service busy. Retrying in {wait_time}s...")
                    print(f"Transient error: {error_str}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise Exception("The AI service is temporarily overloaded - please try again in a few minutes")
            else:
                raise e
                    
    if not narrative_text:
        print("Error: No text response from Narrative Agent.")
        return None, masked_findings
        
    msg = "6. Validating output grounding (hallucination check)..."
    print(msg)
    if on_step: on_step(msg)
    grounding_result = validate_output_grounding(narrative_text, masked_findings)
    
    if not grounding_result["grounded"]:
        print("WARNING: Narrative failed grounding validation! Hallucinated amounts detected:")
        for amt in grounding_result["ungrounded_amounts"]:
            print(f"  - {amt}")
        print("Pipeline halted for safety.")
        return None, masked_findings
        
    msg = "7. Grounding check passed! Unmasking report..."
    print(msg)
    if on_step: on_step(msg)
    unmasked_text = unmask_text(narrative_text, mapping_dict)
    
    # Programmatically insert the date
    current_date = datetime.now().strftime("%Y-%m-%d")
    final_report = f"# Audit Report: Fraud and Compliance Findings\n\n**Report Date:** {current_date}\n\n{unmasked_text.lstrip('# Audit Report: Fraud and Compliance Findings').strip()}"
    
    msg = "8. Saving final report to outputs/audit_report.txt..."
    print(msg)
    if on_step: on_step(msg)
    
    try:
        out_dir = os.path.join(parent_dir, "outputs")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "audit_report.txt")
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(final_report)
            
        print(f"Done! Report saved to {out_path}")
    except Exception as e:
        print(f"Notice: Could not save report to disk (likely read-only cloud filesystem): {e}")
        
    return final_report, masked_findings

if __name__ == "__main__":
    asyncio.run(run_full_pipeline())
