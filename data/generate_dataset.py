import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta
import uuid
import os

fake = Faker()
Faker.seed(42)
np.random.seed(42)
random.seed(42)

NUM_BASE_ROWS = 600
YEAR = 2025

DEPARTMENTS = ['Sales', 'Engineering', 'Marketing', 'Finance', 'Operations']
CATEGORIES = ['Travel', 'Meals', 'Software', 'Office Supplies', 'Client Entertainment', 'Lodging']
REGIONS = ['North America', 'Europe', 'Asia Pacific', 'Latin America']

def get_amount(category):
    ranges = {
        'Software': (50, 2000),
        'Meals': (15, 200),
        'Travel': (100, 3000),
        'Client Entertainment': (50, 800),
        'Lodging': (80, 500),
        'Office Supplies': (10, 300)
    }
    low, high = ranges[category]
    return round(random.uniform(low, high), 2)

# Employees
num_employees = 50
employees = []
for _ in range(num_employees):
    name = fake.name()
    email = f"{name.replace(' ', '.').lower()}@example.com"
    dept = random.choice(DEPARTMENTS)
    card = str(random.randint(1000, 9999))
    region = random.choice(REGIONS)
    employees.append({
        'employee_name': name,
        'employee_email': email,
        'department': dept,
        'card_last4': card,
        'region': region
    })

# Approvers
approvers = [fake.name() for _ in range(10)]

def random_date(year):
    start = datetime(year, 1, 1)
    end = datetime(year, 12, 31)
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

data = []
for _ in range(NUM_BASE_ROWS):
    emp = random.choice(employees)
    cat = random.choice(CATEGORIES)
    data.append({
        'expense_id': str(uuid.uuid4()),
        'employee_name': emp['employee_name'],
        'employee_email': emp['employee_email'],
        'department': emp['department'],
        'category': cat,
        'vendor': fake.company(),
        'amount': get_amount(cat),
        'currency': 'USD',
        'date': random_date(YEAR).strftime('%Y-%m-%d'),
        'card_last4': emp['card_last4'],
        'approver_name': random.choice(approvers),
        'region': emp['region']
    })

df = pd.DataFrame(data)
df['date'] = pd.to_datetime(df['date'])

anomaly_summary = []
new_rows = []

# 1. STRUCTURING
struct_emp = random.choice(employees)
base_date = datetime(YEAR, 3, 10) # a week in March
for i in range(4):
    d = base_date + timedelta(days=i)
    amt = round(random.uniform(480.00, 499.99), 2)
    new_rows.append({
        'expense_id': str(uuid.uuid4()),
        'employee_name': struct_emp['employee_name'],
        'employee_email': struct_emp['employee_email'],
        'department': struct_emp['department'],
        'category': 'Travel',
        'vendor': fake.company(),
        'amount': amt,
        'currency': 'USD',
        'date': d,
        'card_last4': struct_emp['card_last4'],
        'approver_name': random.choice(approvers),
        'region': struct_emp['region']
    })

anomaly_summary.append(f"STRUCTURING: Added 4 expenses for {struct_emp['employee_name']} between {base_date.strftime('%Y-%m-%d')} and {(base_date + timedelta(days=3)).strftime('%Y-%m-%d')}, amounts just under $500.")

# 2. DUPLICATE CLAIMS
dup_indices = random.sample(range(len(df)), 3)
for idx in dup_indices:
    row = df.iloc[idx].to_dict()
    row['expense_id'] = str(uuid.uuid4())
    new_rows.append(row)
    anomaly_summary.append(f"DUPLICATE CLAIM: Duplicated expense for {row['employee_name']} at {row['vendor']} for ${row['amount']} on {row['date'].strftime('%Y-%m-%d')}.")

# 3. CATEGORY SPEND SPIKE
spike_month = 8 # August
spike_dept = 'Marketing'
spike_cat = 'Client Entertainment'

mask = (df['department'] == spike_dept) & (df['category'] == spike_cat)
monthly_spend = df[mask].groupby(df['date'].dt.month)['amount'].sum()
other_months = monthly_spend.index[monthly_spend.index != spike_month]
avg_other = monthly_spend[other_months].mean() if len(other_months) > 0 else 1000
if pd.isna(avg_other):
    avg_other = 1000

target_spend = avg_other * 3
current_aug_spend = monthly_spend.get(spike_month, 0)
needed_spend = target_spend - current_aug_spend

if needed_spend > 0:
    mktg_emps = [e for e in employees if e['department'] == 'Marketing']
    if not mktg_emps:
        mktg_emps = employees # fallback
    emp = random.choice(mktg_emps)
    num_expenses = int(needed_spend // 500) + 1
    amt_per = round(needed_spend / num_expenses, 2)
    for _ in range(num_expenses):
        d = datetime(YEAR, spike_month, random.randint(1, 28))
        new_rows.append({
            'expense_id': str(uuid.uuid4()),
            'employee_name': emp['employee_name'],
            'employee_email': emp['employee_email'],
            'department': emp['department'],
            'category': spike_cat,
            'vendor': fake.company(),
            'amount': amt_per,
            'currency': 'USD',
            'date': d,
            'card_last4': emp['card_last4'],
            'approver_name': random.choice(approvers),
            'region': emp['region']
        })
    anomaly_summary.append(f"CATEGORY SPEND SPIKE: Added {num_expenses} expenses in August to make Marketing's Client Entertainment spend (${target_spend:.2f}) 3x higher than average (${avg_other:.2f}).")

# 4. STATISTICAL OUTLIERS
for _ in range(5):
    cat = random.choice(CATEGORIES)
    ranges = {
        'Software': (50, 2000),
        'Meals': (15, 200),
        'Travel': (100, 3000),
        'Client Entertainment': (50, 800),
        'Lodging': (80, 500),
        'Office Supplies': (10, 300)
    }
    normal_max = ranges[cat][1]
    outlier_amt = round(random.uniform(normal_max * 6, normal_max * 10), 2)
    
    emp = random.choice(employees)
    d = random_date(YEAR)
    new_rows.append({
        'expense_id': str(uuid.uuid4()),
        'employee_name': emp['employee_name'],
        'employee_email': emp['employee_email'],
        'department': emp['department'],
        'category': cat,
        'vendor': fake.company(),
        'amount': outlier_amt,
        'currency': 'USD',
        'date': d,
        'card_last4': emp['card_last4'],
        'approver_name': random.choice(approvers),
        'region': emp['region']
    })
    anomaly_summary.append(f"STATISTICAL OUTLIER: Added {cat} expense for ${outlier_amt} by {emp['employee_name']} (Normal max: ${normal_max}).")

if new_rows:
    df_new = pd.DataFrame(new_rows)
    df_new['date'] = pd.to_datetime(df_new['date'])
    df = pd.concat([df, df_new], ignore_index=True)

# Shuffle dataset
df = df.sample(frac=1, random_state=42).reset_index(drop=True)
df['date'] = df['date'].dt.strftime('%Y-%m-%d')

os.makedirs('data', exist_ok=True)
df.to_csv('data/expenses.csv', index=False)

print("=== ANOMALY SUMMARY ===")
for msg in anomaly_summary:
    print("- " + msg)
print("=======================")
