import os
import pandas as pd
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("auditx-data-server")

# Get path relative to this script
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'expenses.csv')

def load_data() -> pd.DataFrame:
    """Helper function to load the dataset fresh on each call."""
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Data file not found at {DATA_PATH}")
    return pd.read_csv(DATA_PATH)

@mcp.tool()
def get_schema() -> Dict[str, str]:
    """
    Returns the column names and data types of the expense dataset.
    
    This tool is useful for understanding the structure of the dataset before writing queries or filters.
    
    Returns:
        A dictionary mapping column names to their pandas data types as strings.
    """
    df = load_data()
    return {col: str(dtype) for col, dtype in df.dtypes.items()}

@mcp.tool()
def get_expenses(
    department: Optional[str] = None,
    category: Optional[str] = None,
    employee_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Returns matching rows from the expense dataset based on optional filters.
    If no filters are provided, returns all rows.
    
    Args:
        department: Filter by exact department name (e.g., 'Marketing').
        category: Filter by exact category name (e.g., 'Travel').
        employee_name: Filter by exact employee name.
        start_date: Filter rows on or after this date (format: YYYY-MM-DD).
        end_date: Filter rows on or before this date (format: YYYY-MM-DD).
        min_amount: Minimum expense amount (inclusive).
        max_amount: Maximum expense amount (inclusive).
        
    Returns:
        A list of dictionaries representing the matching rows.
    """
    df = load_data()
    
    if department:
        df = df[df['department'] == department]
    if category:
        df = df[df['category'] == category]
    if employee_name:
        df = df[df['employee_name'] == employee_name]
    
    if start_date:
        df = df[df['date'] >= start_date]
    if end_date:
        df = df[df['date'] <= end_date]
        
    if min_amount is not None:
        df = df[df['amount'] >= min_amount]
    if max_amount is not None:
        df = df[df['amount'] <= max_amount]
        
    # Replace NaN with None for JSON serialization
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient='records')

@mcp.tool()
def get_summary_stats(group_by: Optional[str] = None) -> Any:
    """
    Returns count, sum, mean, and standard deviation of the 'amount' column.
    Can optionally group the statistics by a specific column.
    
    Args:
        group_by: Column name to group the statistics by (e.g., 'department', 'category').
                  If None, returns overall statistics for the entire dataset.
                  
    Returns:
        A dictionary (or list of dictionaries if grouped) containing the calculated statistics.
    """
    df = load_data()
    
    if group_by:
        if group_by not in df.columns:
            return {"error": f"Column '{group_by}' not found in dataset."}
        
        stats = df.groupby(group_by)['amount'].agg(['count', 'sum', 'mean', 'std']).reset_index()
        stats = stats.where(pd.notnull(stats), None)
        return stats.to_dict(orient='records')
    else:
        stats = {
            "count": int(df['amount'].count()),
            "sum": float(df['amount'].sum()),
            "mean": float(df['amount'].mean()),
            "std": float(df['amount'].std()) if pd.notna(df['amount'].std()) else 0.0
        }
        return stats

if __name__ == "__main__":
    # Disable rich logging for fastmcp since it breaks stdio communication
    import logging
    logging.getLogger('fastmcp').setLevel(logging.CRITICAL)
    logging.getLogger().setLevel(logging.CRITICAL)
    # Run the server over stdio without the banner
    mcp.run(transport='stdio', show_banner=False)
