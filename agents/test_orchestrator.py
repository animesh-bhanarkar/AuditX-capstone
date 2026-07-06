import asyncio
import os
import sys
import pandas as pd
import json

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from agents.orchestrator import run_full_pipeline

async def test_pipeline():
    print("==================================================")
    print("Testing Full Orchestrator Pipeline")
    print("==================================================")
    
    # 1. Run pipeline
    final_report, masked_findings = await run_full_pipeline()
    
    if final_report is None:
        print("\nPipeline failed or aborted due to grounding error.")
        return
        
    # 2. Check PII removal from LLM input (masked_findings)
    print("\n--- Verifying PII Masking in LLM Input ---")
    df = pd.read_csv(os.path.join(parent_dir, "data", "expenses.csv"))
    real_names = df['employee_name'].dropna().unique().tolist()
    if 'approver_name' in df.columns:
        real_names.extend(df['approver_name'].dropna().unique().tolist())
    
    # Remove short names/common words that might naturally occur
    real_names = [name for name in set(real_names) if len(name) > 4]
    
    findings_json = json.dumps(masked_findings)
    leaked_names = []
    
    for name in real_names:
        if name in findings_json:
            leaked_names.append(name)
            
    if not leaked_names:
        print("✅ SUCCESS: Zero real employee/approver names found in the masked findings JSON sent to LLM!")
    else:
        print(f"❌ WARNING: Found real names leaked into LLM input: {leaked_names}")
        
    # 3. Check final report
    print("\n--- Final Unmasked Audit Report (First 40 lines) ---")
    lines = final_report.strip().split("\n")
    for line in lines[:40]:
        print(line)
    if len(lines) > 40:
        print(f"\n... (and {len(lines) - 40} more lines) ...")
        
    # 4. Check file existence
    out_path = os.path.join(parent_dir, "outputs", "audit_report.txt")
    if os.path.exists(out_path):
        print(f"\n✅ SUCCESS: outputs/audit_report.txt was successfully created (Size: {os.path.getsize(out_path)} bytes).")
    else:
        print("\n❌ ERROR: outputs/audit_report.txt was not found.")

if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    
    asyncio.run(test_pipeline())
