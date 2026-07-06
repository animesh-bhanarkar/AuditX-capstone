import json
from server import get_schema, get_expenses, get_summary_stats

def main():
    print("=== Testing get_schema ===")
    try:
        schema = get_schema()
        print(json.dumps(schema, indent=2))
    except Exception as e:
        print(f"Error in get_schema: {e}")
    print("\n" + "="*50 + "\n")

    print("=== Testing get_expenses (No filters) ===")
    try:
        all_expenses = get_expenses()
        print(f"Total expenses retrieved: {len(all_expenses)}")
        if all_expenses:
            print("First expense:")
            print(json.dumps(all_expenses[0], indent=2))
    except Exception as e:
        print(f"Error in get_expenses: {e}")
    print("\n" + "="*50 + "\n")

    print("=== Testing get_expenses (With filters) ===")
    try:
        filtered_expenses = get_expenses(
            department='Marketing',
            category='Client Entertainment',
            min_amount=500.0,
            start_date='2025-08-01',
            end_date='2025-08-31'
        )
        print(f"Filtered expenses retrieved (Marketing, Client Entertainment in Aug > $500): {len(filtered_expenses)}")
        if filtered_expenses:
             print("First filtered expense:")
             print(json.dumps(filtered_expenses[0], indent=2))
    except Exception as e:
        print(f"Error in get_expenses (filtered): {e}")
    print("\n" + "="*50 + "\n")

    print("=== Testing get_summary_stats (Overall) ===")
    try:
        overall_stats = get_summary_stats()
        print(json.dumps(overall_stats, indent=2))
    except Exception as e:
        print(f"Error in get_summary_stats: {e}")
    print("\n" + "="*50 + "\n")

    print("=== Testing get_summary_stats (Grouped by department) ===")
    try:
        grouped_stats = get_summary_stats(group_by='department')
        print(json.dumps(grouped_stats, indent=2))
    except Exception as e:
        print(f"Error in get_summary_stats (grouped): {e}")
    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()
