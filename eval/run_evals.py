import os
import sys
import json
import asyncio
import pandas as pd

# Add the project root to sys.path so we can import agents/
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from agents.skills import fraud_detection
from agents.guardrails import pii_guard
from agents import orchestrator

total_tests = 0
passed_tests = 0
failed_tests = 0

def check(condition, test_name):
    global total_tests, passed_tests, failed_tests
    total_tests += 1
    if condition:
        print(f"[PASS] {test_name}")
        passed_tests += 1
    else:
        print(f"[FAIL] {test_name}")
        failed_tests += 1

async def run_evals():
    print("==================================================")
    print("EVALUATION SCRIPT: RUNNING TEST SUITE")
    print("==================================================\n")
    
    # Load dataset
    data_path = os.path.join(project_root, "data", "expenses.csv")
    df = pd.read_csv(data_path)
    
    print("SECTION 1: Fraud detection accuracy (pure function tests)")
    print("-" * 50)
    findings = fraud_detection.run_all_detections(df)
    
    # Convert findings to a searchable string dump for easy validation
    findings_str = json.dumps(findings)
    
    # Structuring checks
    for name in ["Debra Davidson", "Lisa Jackson", "Shane Henderson", "Brittany Farmer", "Brian Ramirez"]:
        check(name in findings_str, f"{name} structuring detected")
        
    # Duplicate claims checks
    for name in ["Anthony Rodriguez", "Jeffrey Chavez", "Lisa Jackson"]:
        check(name in findings_str, f"{name} duplicate claim detected")
        
    # Category spike check — the detection stores the period as '2025-08', not 'August'
    check("Marketing" in findings_str and "Client Entertainment" in findings_str and "2025-08" in findings_str,
          "Category spend spike (Marketing/Client Entertainment/August) detected")
          
    # Statistical outliers check
    for name in ["Connie Lawrence", "Zachary Hicks", "Cassandra Gaines", "Nathan Maldonado", "Noah Rhodes"]:
        check(name in findings_str, f"{name} statistical outlier detected")
        
    print("\nSECTION 2: PII guardrail correctness (no LLM calls)")
    print("-" * 50)
    
    masked_df, mapping_dict = pii_guard.mask_dataframe(df)
    
    # Check mask_dataframe
    masked_df_str = masked_df.to_string()
    check("Debra Davidson" not in masked_df_str and "Brian Ramirez" not in masked_df_str, 
          "No real employee names found in masked dataframe")
          
    # Check mask_findings
    masked_findings = pii_guard.mask_findings(findings, mapping_dict)
    masked_findings_str = json.dumps(masked_findings)
    check("Debra Davidson" not in masked_findings_str and "EMP_" in masked_findings_str, 
          "No real names appear in masked findings JSON")
          
    # Check unmask_text
    sample_token = list(mapping_dict.keys())[0]  # e.g. EMP_001
    real_value = mapping_dict[sample_token]
    round_trip = pii_guard.unmask_text(f"Hello {sample_token}", mapping_dict)
    check(round_trip == f"Hello {real_value}", "Round-trip unmasking returns exact original name")
    
    # Check validate_output_grounding
    # Evidence must be a list of dicts with an 'amount' key — matching the real findings schema
    # Note: validate_output_grounding returns a DICT {"grounded": bool, ...}, not a plain bool
    valid_text = "The amount is $50.00."
    invalid_text = "The amount is $999,999.99."
    dummy_findings = [{"evidence": [{"amount": 50.00, "vendor": "Acme"}]}]
    
    check(pii_guard.validate_output_grounding(valid_text, dummy_findings)["grounded"] == True,
          "validate_output_grounding correctly returns True for grounded text")
    check(pii_guard.validate_output_grounding(invalid_text, dummy_findings)["grounded"] == False,
          "validate_output_grounding correctly returns False for hallucinated text")
          
    print("\nSECTION 3: End-to-end pipeline integrity (1 LLM call)")
    print("-" * 50)
    print("Running orchestrator pipeline. Please wait...")
    
    final_report, pipe_masked_findings = await orchestrator.run_full_pipeline()
    
    if final_report is None:
        check(False, "Pipeline returned a report (implies grounding passed)")
        check(False, "Zero leftover masked tokens (EMP_, APPROVER_) in final report")
        check(False, "Final report contains real employee names")
    else:
        check(True, "Pipeline returned a report (implies grounding passed)")
        
        has_leftover_tokens = "EMP_" in final_report or "APPROVER_" in final_report
        check(not has_leftover_tokens, "Zero leftover masked tokens (EMP_, APPROVER_) in final report")
        
        # Check if real names were successfully injected back
        has_real_names = any(name in final_report for name in ["Debra Davidson", "Anthony Rodriguez", "Brittany Farmer"])
        check(has_real_names, "Final report contains real employee names from ground truth")
        
    print("\n==================================================")
    print("SUMMARY")
    print("==================================================")
    print(f"Total Tests: {total_tests}")
    print(f"Passed     : {passed_tests}")
    print(f"Failed     : {failed_tests}")
    
    if failed_tests == 0:
        print("\n*** ALL TESTS PASSED ***")
        sys.exit(0)
    else:
        print(f"\n!!! {failed_tests} TESTS FAILED !!!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_evals())
