"""
agents/skills/fraud_detection.py

Pure-Python, deterministic fraud/anomaly detection functions.
No LLM calls. Takes a pandas DataFrame of expense records and returns
structured findings (list of dicts).

Each finding dict has:
  - type        : str   – detector name
  - severity    : str   – "low" | "medium" | "high"
  - description : str   – human-readable summary
  - evidence    : list  – the specific rows / values that triggered the finding
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# 1. Structuring Detection
# ---------------------------------------------------------------------------

def detect_structuring(
    df: pd.DataFrame,
    threshold: float = 500.0,
    window_days: int = 7,
    min_occurrences: int = 3,
) -> List[Dict[str, Any]]:
    """
    Flag employees who submit multiple expenses individually below `threshold`
    but cluster within a rolling `window_days` window — classic structuring
    to avoid single-transaction approval limits.

    Args:
        df              : expense DataFrame with columns date, employee_name, amount, ...
        threshold       : per-transaction approval limit (default $500)
        window_days     : rolling window in calendar days (default 7)
        min_occurrences : minimum sub-threshold transactions in the window (default 3)

    Returns:
        List of finding dicts.
    """
    findings = []

    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])

    # Only consider expenses individually below the threshold
    sub = work[work["amount"] < threshold].copy()
    sub = sub.sort_values(["employee_name", "date"])

    for employee, group in sub.groupby("employee_name"):
        group = group.sort_values("date").reset_index(drop=True)
        dates = group["date"].values  # numpy datetime64

        # Sliding-window scan: for each row i, count rows within window_days ahead
        n = len(group)
        for i in range(n):
            window_end = dates[i] + np.timedelta64(window_days, "D")
            mask = (dates >= dates[i]) & (dates <= window_end)
            window_rows = group[mask]

            if len(window_rows) >= min_occurrences:
                window_total = window_rows["amount"].sum()
                evidence_rows = window_rows[
                    ["expense_id", "employee_name", "department", "date", "amount", "vendor"]
                ].copy()
                evidence_rows["date"] = evidence_rows["date"].astype(str)

                findings.append({
                    "type": "STRUCTURING",
                    "severity": "high",
                    "description": (
                        f"{employee} submitted {len(window_rows)} expenses each under "
                        f"${threshold:,.2f} within a {window_days}-day window "
                        f"({window_rows['date'].min().strftime('%Y-%m-%d')} to "
                        f"{window_rows['date'].max().strftime('%Y-%m-%d')}), "
                        f"totalling ${window_total:,.2f}."
                    ),
                    "evidence": evidence_rows.to_dict(orient="records"),
                })
                # Advance i past this window to avoid duplicate findings for same cluster
                break

    return findings


# ---------------------------------------------------------------------------
# 2. Duplicate Claims Detection
# ---------------------------------------------------------------------------

def detect_duplicate_claims(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Flag rows that share the same employee_name, vendor, amount, and date
    as at least one other row — likely duplicate submissions.

    Args:
        df : expense DataFrame

    Returns:
        List of finding dicts, one per duplicate group.
    """
    findings = []

    work = df.copy()
    work["date"] = pd.to_datetime(work["date"]).dt.date  # date-only for comparison

    key_cols = ["employee_name", "vendor", "amount", "date"]
    dupes = work[work.duplicated(subset=key_cols, keep=False)].copy()

    if dupes.empty:
        return findings

    for group_key, group in dupes.groupby(key_cols):
        employee, vendor, amount, date = group_key
        evidence_rows = group[
            ["expense_id", "employee_name", "department", "date", "amount", "vendor"]
        ].copy()
        evidence_rows["date"] = evidence_rows["date"].astype(str)

        findings.append({
            "type": "DUPLICATE_CLAIM",
            "severity": "high",
            "description": (
                f"{employee} submitted {len(group)} identical expenses at "
                f"{vendor} for ${amount:,.2f} on {date}."
            ),
            "evidence": evidence_rows.to_dict(orient="records"),
        })

    return findings


# ---------------------------------------------------------------------------
# 3. Category Spend Spike Detection
# ---------------------------------------------------------------------------

def detect_category_spend_spike(
    df: pd.DataFrame,
    factor: float = 2.5,
) -> List[Dict[str, Any]]:
    """
    For each (department, category) pair, compute each calendar month's total
    spend and flag months where that total exceeds `factor` × the average of
    all *other* months for the same pair.

    Args:
        df     : expense DataFrame
        factor : spike multiplier relative to average of other months (default 2.5)

    Returns:
        List of finding dicts.
    """
    findings = []

    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])
    work["month"] = work["date"].dt.to_period("M")

    monthly = (
        work.groupby(["department", "category", "month"])["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "monthly_total"})
    )

    for (dept, cat), group in monthly.groupby(["department", "category"]):
        group = group.sort_values("month")
        for _, row in group.iterrows():
            this_month = row["month"]
            this_total = row["monthly_total"]
            other_totals = group.loc[group["month"] != this_month, "monthly_total"]

            if other_totals.empty:
                continue  # only one month of data – can't compute baseline

            avg_other = other_totals.mean()
            if avg_other == 0:
                continue

            if this_total >= factor * avg_other:
                # Collect contributing rows from the flagged month
                mask = (
                    (work["department"] == dept)
                    & (work["category"] == cat)
                    & (work["month"] == this_month)
                )
                contrib_rows = work[mask][
                    ["expense_id", "employee_name", "department", "category",
                     "date", "amount", "vendor"]
                ].copy()
                contrib_rows["date"] = contrib_rows["date"].dt.strftime("%Y-%m-%d")

                findings.append({
                    "type": "CATEGORY_SPEND_SPIKE",
                    "severity": "medium",
                    "description": (
                        f"{dept} / {cat}: spend in {this_month} was "
                        f"${this_total:,.2f}, which is "
                        f"{this_total / avg_other:.1f}× the average of other months "
                        f"(${avg_other:,.2f}). Threshold: {factor}×."
                    ),
                    "evidence": contrib_rows.to_dict(orient="records"),
                })

    return findings


# ---------------------------------------------------------------------------
# 4. Statistical Outlier Detection
# ---------------------------------------------------------------------------

def detect_statistical_outliers(
    df: pd.DataFrame,
    z_thresh: float = 3.0,
) -> List[Dict[str, Any]]:
    """
    For each expense category, compute z-scores of amount. Flag any row
    whose absolute z-score exceeds `z_thresh`.

    Args:
        df        : expense DataFrame
        z_thresh  : z-score threshold (default 3.0)

    Returns:
        List of finding dicts, one per flagged row.
    """
    findings = []

    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])

    for category, group in work.groupby("category"):
        if len(group) < 2:
            continue

        mean_amt = group["amount"].mean()
        std_amt = group["amount"].std()

        if std_amt == 0:
            continue

        group = group.copy()
        group["z_score"] = (group["amount"] - mean_amt) / std_amt
        flagged = group[group["z_score"].abs() > z_thresh]

        for _, row in flagged.iterrows():
            findings.append({
                "type": "STATISTICAL_OUTLIER",
                "severity": "medium",
                "description": (
                    f"{row['employee_name']} submitted a {category} expense of "
                    f"${row['amount']:,.2f} — z-score {row['z_score']:.2f} "
                    f"(category mean: ${mean_amt:,.2f}, std: ${std_amt:,.2f})."
                ),
                "evidence": [{
                    "expense_id": row.get("expense_id", ""),
                    "employee_name": row["employee_name"],
                    "department": row["department"],
                    "category": category,
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "amount": row["amount"],
                    "vendor": row.get("vendor", ""),
                    "z_score": round(float(row["z_score"]), 4),
                }],
            })

    return findings


# ---------------------------------------------------------------------------
# Combined runner
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def run_all_detections(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Run all four detectors and return a combined, severity-sorted list of
    findings (high → medium → low).

    Args:
        df : expense DataFrame with at minimum the columns:
             expense_id, employee_name, department, category,
             vendor, amount, date

    Returns:
        Sorted list of finding dicts.
    """
    all_findings: List[Dict[str, Any]] = []
    all_findings.extend(detect_structuring(df))
    all_findings.extend(detect_duplicate_claims(df))
    all_findings.extend(detect_category_spend_spike(df))
    all_findings.extend(detect_statistical_outliers(df))

    all_findings.sort(key=lambda f: _SEVERITY_ORDER.get(f["severity"], 9))
    return all_findings
