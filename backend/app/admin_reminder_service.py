from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

try:
    from backend.app.email_service import send_email
    from backend.app.refill_engine import get_refill_dataframe
except ModuleNotFoundError:
    from email_service import send_email
    from refill_engine import get_refill_dataframe


def _load_contacts(contact_file: str) -> pd.DataFrame:
    path = Path(contact_file)
    if not path.exists():
        return pd.DataFrame(columns=["patient_id", "email"])

    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    if "patient_id" not in df.columns:
        return pd.DataFrame(columns=["patient_id", "email"])
    if "email" not in df.columns:
        df["email"] = None
    return df


def _prepare_due_df(
    history_file: str,
    max_overdue_days: int = 9999,
    only_latest_per_patient_product: bool = True,
) -> pd.DataFrame:
    df = get_refill_dataframe(history_file).copy()
    df = df[df["next_refill_date"].notnull()].copy()

    if only_latest_per_patient_product:
        df = (
            df.sort_values("purchase_date")
            .groupby(["patient_id", "product_name"], as_index=False)
            .tail(1)
        )

    today = date.today()
    df["days_overdue"] = (today - df["next_refill_date"].dt.date).apply(lambda x: x.days)
    due = df[(df["days_overdue"] >= 0) & (df["days_overdue"] <= max_overdue_days)].copy()
    return due


def preview_admin_reminders(
    history_file: str,
    contact_file: str,
    max_overdue_days: int = 9999,
) -> Dict:
    due = _prepare_due_df(history_file=history_file, max_overdue_days=max_overdue_days)
    contacts = _load_contacts(contact_file)

    merged = due.merge(contacts, on="patient_id", how="left")
    merged["email"] = merged["email"].fillna("")

    rows: List[Dict] = []
    for _, row in merged.iterrows():
        rows.append(
            {
                "patient_id": row.get("patient_id"),
                "product_name": row.get("product_name"),
                "next_refill_date": str(row.get("next_refill_date").date()),
                "days_overdue": int(row.get("days_overdue", 0)),
                "email": row.get("email", ""),
                "can_send": bool(str(row.get("email", "")).strip()),
            }
        )

    return {
        "total_due": len(rows),
        "sendable": sum(1 for r in rows if r["can_send"]),
        "missing_contact": sum(1 for r in rows if not r["can_send"]),
        "results": rows,
    }


def send_admin_reminders(
    history_file: str,
    contact_file: str,
    admin_name: str,
    admin_contact: str,
    max_overdue_days: int = 9999,
    dry_run: bool = True,
) -> Dict:
    preview = preview_admin_reminders(
        history_file=history_file,
        contact_file=contact_file,
        max_overdue_days=max_overdue_days,
    )

    sent = 0
    failed = 0
    skipped = 0
    details: List[Dict] = []

    for row in preview["results"]:
        if not row["can_send"]:
            skipped += 1
            details.append({**row, "status": "skipped_missing_contact"})
            continue

        message = (
            f"Hello {row['patient_id']},\n\n"
            f"This is a refill reminder for: {row['product_name']}.\n"
            f"Your refill was due on: {row['next_refill_date']}.\n\n"
            f"For help, contact admin: {admin_name} ({admin_contact})."
        )

        if dry_run:
            sent += 1
            details.append({**row, "status": "dry_run_ready"})
            continue

        result = send_email(
            to_email=row["email"],
            message=message,
            subject="Medicine Refill Reminder",
        )
        if result.get("success"):
            sent += 1
            details.append({**row, "status": "sent"})
        else:
            failed += 1
            details.append({**row, "status": "failed", "error": result.get("error")})

    return {
        "dry_run": dry_run,
        "total_due": preview["total_due"],
        "sendable": preview["sendable"],
        "sent_or_ready": sent,
        "failed": failed,
        "skipped": skipped,
        "details": details,
    }
