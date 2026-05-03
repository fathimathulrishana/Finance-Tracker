"""
fix_float_data.py — One-time data repair script.

PURPOSE:
    Scans all monetary fields across every financial model for values
    that were stored with floating-point imprecision (e.g., 49999.99
    instead of 50000.00) and rounds them to exactly 2 decimal places
    using ROUND_HALF_UP — the standard rounding used in financial systems.

SAFETY:
    - Only updates rows where the stored value differs from its correctly
      rounded form (i.e., rows with no corruption are NEVER touched).
    - Prints a full before/after audit log for every corrected row.
    - Dry-run mode (DRY_RUN = True) lets you preview without saving.

USAGE:
    python fix_float_data.py          # Live run — writes to DB
    DRY_RUN=True python fix_float_data.py  # Preview only
"""

import os
import sys
import django

# ── Django setup ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_ai.settings')
django.setup()

from decimal import Decimal, ROUND_HALF_UP
from expenses.models import Expense, Income, SavingGoal, Bill, Budget

# Set DRY_RUN = True to preview changes without writing to the database
DRY_RUN = os.environ.get('DRY_RUN', '').lower() in ('true', '1', 'yes')

QUANTIZE_TARGET = Decimal('0.01')


def fix_field(obj, field_name: str, model_name: str, dry_run: bool) -> bool:
    """
    Round one monetary field on an object.
    Returns True if a correction was needed.
    """
    raw = getattr(obj, field_name)
    if raw is None:
        return False

    # Ensure we work with a Decimal — SQLite may hand back float for old rows
    if not isinstance(raw, Decimal):
        raw = Decimal(str(raw))

    corrected = raw.quantize(QUANTIZE_TARGET, rounding=ROUND_HALF_UP)

    if raw != corrected:
        saved_note = " (DRY RUN - not saved)" if dry_run else ""
        print(
            f"  [{model_name} id={obj.pk}] {field_name}: "
            f"{raw} -> {corrected}{saved_note}"
        )
        if not dry_run:
            setattr(obj, field_name, corrected)
        return True
    return False


def repair_model(model_class, fields: list[str], dry_run: bool):
    model_name = model_class.__name__
    fixed_rows = 0
    total = model_class.objects.count()
    print(f"\n--- {model_name} ({total} rows) ---")

    for obj in model_class.objects.all():
        changed = False
        for field in fields:
            if fix_field(obj, field, model_name, dry_run):
                changed = True

        if changed:
            if not dry_run:
                obj.save(update_fields=fields)
            fixed_rows += 1

    if fixed_rows == 0:
        print(f"  [OK] No corrections needed.")
    else:
        action = "Would fix" if dry_run else "Fixed"
        print(f"  [FIX] {action} {fixed_rows} row(s).")

    return fixed_rows


if __name__ == '__main__':
    print("=" * 60)
    print("  Finance Tracker - Float Precision Data Repair")
    print(f"  Mode: {'DRY RUN (preview only)' if DRY_RUN else 'LIVE (writing to DB)'}")
    print("=" * 60)

    total_fixed = 0
    total_fixed += repair_model(Income,     ['amount'],                            DRY_RUN)
    total_fixed += repair_model(Expense,    ['amount'],                            DRY_RUN)
    total_fixed += repair_model(SavingGoal, ['target_amount', 'saved_amount'],     DRY_RUN)
    total_fixed += repair_model(Bill,       ['amount'],                            DRY_RUN)
    total_fixed += repair_model(Budget,     ['monthly_budget'],                    DRY_RUN)

    print()
    print("=" * 60)
    if total_fixed == 0:
        print("  [OK] Database is clean - no corrections needed.")
    elif DRY_RUN:
        print(f"  [PREVIEW] DRY RUN complete - {total_fixed} row(s) would be corrected.")
        print("  Run without DRY_RUN=True to apply changes.")
    else:
        print(f"  [OK] Data repair complete - {total_fixed} row(s) corrected.")
    print("=" * 60)
