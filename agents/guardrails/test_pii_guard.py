import sys
import os
import pandas as pd
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.guardrails.pii_guard import mask_dataframe, unmask_text, validate_output_grounding
from agents.skills.fraud_detection import run_all_detections

def main():
    print("=======================================")
    print("Testing PII Guardrails")
    print("=======================================")
    
    # Load dataset
    data_path = 'data/expenses.csv'
    if not os.path.exists(data_path):
        print(f"Dataset not found at {data_path}")
        return
        
    df = pd.read_csv(data_path)
    
    # 1. Test mask_dataframe
    print("\n--- 1. Testing mask_dataframe ---")
    masked_df, mapping_dict = mask_dataframe(df)
    
    print("\nOriginal DataFrame (first 5 rows, specific columns):")
    cols_to_show = ['employee_name', 'employee_email', 'card_last4', 'approver_name']
    print(df[cols_to_show].head().to_string())
    
    print("\nMasked DataFrame (first 5 rows, specific columns):")
    print(masked_df[cols_to_show].head().to_string())
    
    # 2. Test unmask_text
    print("\n--- 2. Testing unmask_text ---")
    # Get a real mapping from the dict
    emp_token = None
    real_name = None
    for token, name in mapping_dict.items():
        if token.startswith("EMP_"):
            emp_token = token
            real_name = name
            break
            
    if emp_token:
        fake_narrative = f"{emp_token} submitted 4 expenses totaling $1,948.82 which appears to be structuring."
        print(f"Masked Text:   {fake_narrative}")
        unmasked = unmask_text(fake_narrative, mapping_dict)
        print(f"Unmasked Text: {unmasked}")
        assert real_name in unmasked, f"Expected {real_name} in unmasked text"
        print("-> unmask_text SUCCESS")
    else:
        print("No EMP token found in mapping_dict")
        
    # 3. Test validate_output_grounding
    print("\n--- 3. Testing validate_output_grounding ---")
    # Get actual findings to test against
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    findings_list = run_all_detections(df)
    
    # True case - $4,150.47 and $15,327.80 are in the actual anomalies
    valid_narrative = "The employee had large expenses of $4,150.47 for lodging and $15,327.80 for software."
    res_valid = validate_output_grounding(valid_narrative, findings_list)
    print(f"\nNarrative: {valid_narrative}")
    print(f"Result (should be grounded: True): {res_valid}")
    
    # False case - $99,999.99 is not in the findings
    invalid_narrative = "The employee submitted a fake expense of $99,999.99 which is an outlier."
    res_invalid = validate_output_grounding(invalid_narrative, findings_list)
    print(f"\nNarrative: {invalid_narrative}")
    print(f"Result (should be grounded: False, with $99,999.99): {res_invalid}")

if __name__ == "__main__":
    main()
