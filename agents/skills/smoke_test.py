import pandas as pd, sys
sys.path.insert(0, '.')
from agents.skills.fraud_detection import run_all_detections

df = pd.read_csv('data/expenses.csv')
findings = run_all_detections(df)
sev = {'high': 0, 'medium': 0, 'low': 0}
for f in findings:
    sev[f['severity']] += 1

print(f'Total findings: {len(findings)}')
for k, v in sev.items():
    print(f'  {k}: {v}')
print()
for f in findings:
    print(f"  [{f['severity'].upper()}] {f['type']}: {f['description'][:110]}")
