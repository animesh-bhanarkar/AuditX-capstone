import re
import pandas as pd

def mask_dataframe(df):
    """
    Masks PII in the expense dataframe with consistent pseudonymous tokens.
    Returns: (masked_df, mapping_dict)
    """
    masked_df = df.copy()
    mapping_dict = {}
    
    # Track unique assignments
    emp_map = {}
    approver_map = {}
    
    emp_counter = 1
    approver_counter = 1
    
    # First, build mappings for all unique employees and approvers
    if 'employee_name' in masked_df.columns:
        for name in masked_df['employee_name'].dropna().unique():
            if name not in emp_map:
                token = f"EMP_{emp_counter:03d}"
                emp_map[name] = token
                mapping_dict[token] = name
                emp_counter += 1
                
    if 'approver_name' in masked_df.columns:
        for name in masked_df['approver_name'].dropna().unique():
            if name not in approver_map:
                token = f"APPROVER_{approver_counter:02d}"
                approver_map[name] = token
                mapping_dict[token] = name
                approver_counter += 1

    # Apply mappings to dataframe
    if 'employee_name' in masked_df.columns:
        masked_df['employee_name'] = masked_df['employee_name'].map(emp_map).fillna(masked_df['employee_name'])
        
    if 'approver_name' in masked_df.columns:
        masked_df['approver_name'] = masked_df['approver_name'].map(approver_map).fillna(masked_df['approver_name'])
        
    if 'employee_email' in masked_df.columns and 'employee_name' in df.columns:
        # Create email mappings corresponding to employee names
        email_map = {}
        for idx, row in df.iterrows():
            orig_name = row['employee_name']
            orig_email = row['employee_email']
            if pd.notna(orig_name) and pd.notna(orig_email) and orig_name in emp_map:
                emp_token = emp_map[orig_name]
                # Extract the number part from EMP_001
                token_num = emp_token.split('_')[1]
                masked_email = f"emp{token_num}@masked.local"
                email_map[orig_email] = masked_email
                if masked_email not in mapping_dict:
                    mapping_dict[masked_email] = orig_email
                    
        masked_df['employee_email'] = masked_df['employee_email'].map(email_map).fillna(masked_df['employee_email'])
        
    if 'card_last4' in masked_df.columns:
        masked_df['card_last4'] = "XXXX"

    return masked_df, mapping_dict

def unmask_text(text, mapping_dict):
    """
    Restores original PII from masked tokens in text using the mapping_dict.
    Uses word boundaries to avoid partial matches.
    """
    if not text or not mapping_dict:
        return text
        
    unmasked_text = text
    
    # Sort keys by length descending to replace longer tokens first (e.g. EMP_010 before EMP_01)
    sorted_keys = sorted(mapping_dict.keys(), key=len, reverse=True)
    
    for token in sorted_keys:
        original_value = str(mapping_dict[token])
        # Use regex for whole-word replacement if token is alphanumeric/underscore
        # For emails, word boundary at the ends might be tricky, but \b works well for EMP_001
        escaped_token = re.escape(token)
        # We handle boundaries specifically: (?<!\w)token(?!\w) for \b like behavior that also works with @
        pattern = r'(?<!\w)' + escaped_token + r'(?!\w)'
        unmasked_text = re.sub(pattern, original_value, unmasked_text)
        
    return unmasked_text

def validate_output_grounding(narrative_text, findings_list):
    """
    Extracts all dollar amounts from the narrative_text and ensures they exist 
    in the findings_list evidence.
    """
    # Regex to find dollar amounts e.g., $1,234.56 or $1234.56 or $12.3 or $500
    amount_pattern = r'\$\d{1,3}(?:,\d{3})*(?:\.\d+)?'
    
    found_amounts = re.findall(amount_pattern, narrative_text)
    
    if not found_amounts:
        return {"grounded": True, "ungrounded_amounts": []}
        
    # Convert findings list to a single string representation to check against
    import json
    # Specifically looking in the evidence parts or description of findings
    findings_str = json.dumps(findings_list)
    
    ungrounded = []
    
    for amount in found_amounts:
        # Strip the $ sign for checking in the raw data, as the raw data might just be numeric 4150.47
        # Also check with $ sign since findings descriptions might contain the $ sign.
        numeric_val = amount.replace('$', '').replace(',', '')
        
        # Check if the exact string (e.g. "$1,234.56") is in findings_str
        if amount in findings_str:
            continue
            
        # Check if the numeric float string (e.g. "1234.56") is in findings_str
        # Sometimes evidence has 1234.56 but narrative has $1,234.56
        if numeric_val in findings_str:
            continue
            
        # Check if float version like 1234.5 is in findings_str (if .0 it might be omitted)
        try:
            float_val = float(numeric_val)
            # Find evidence amounts
            amounts_in_evidence = []
            for f in findings_list:
                for ev in f.get('evidence', []):
                    ev_amt = ev.get('amount')
                    if ev_amt is not None:
                        amounts_in_evidence.append(float(ev_amt))
            
            if float_val in amounts_in_evidence:
                continue
        except (ValueError, TypeError):
            pass
            
        ungrounded.append(amount)
        
    # Deduplicate ungrounded amounts
    ungrounded = list(set(ungrounded))
    
    return {
        "grounded": len(ungrounded) == 0,
        "ungrounded_amounts": ungrounded
    }

def mask_findings(findings_list, mapping_dict):
    """
    Replaces real names in findings description and evidence fields with their masked tokens.
    """
    import copy
    
    masked_findings = copy.deepcopy(findings_list)
    
    if not mapping_dict:
        return masked_findings
        
    # Reverse the mapping dict so we can replace Real Name -> Token
    # Only map names (EMP_ and APPROVER_), ignore emails for now as they typically aren't in descriptions
    reverse_map = {}
    for k, v in mapping_dict.items():
        if k.startswith("EMP_") or k.startswith("APPROVER_"):
            reverse_map[str(v)] = str(k)
            
    # Sort keys (real names) by length descending to replace longest matching string first
    sorted_real_names = sorted(reverse_map.keys(), key=len, reverse=True)
    
    def replace_in_text(text):
        if not isinstance(text, str):
            return text
        res = text
        for real_name in sorted_real_names:
            token = reverse_map[real_name]
            escaped_name = re.escape(real_name)
            # Use \b equivalent handling like in unmask_text
            pattern = r'(?<!\w)' + escaped_name + r'(?!\w)'
            res = re.sub(pattern, token, res)
        return res

    for f in masked_findings:
        if 'description' in f:
            f['description'] = replace_in_text(f['description'])
            
        for ev in f.get('evidence', []):
            if 'employee_name' in ev:
                ev['employee_name'] = replace_in_text(str(ev['employee_name']))
            if 'approver_name' in ev:
                ev['approver_name'] = replace_in_text(str(ev['approver_name']))
                
    return masked_findings
