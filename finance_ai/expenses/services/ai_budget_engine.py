"""
ai_budget_engine.py — Hybrid AI + Rule-Based Budget Analysis Engine.

Architecture:
  1. Always run rule_engine (guaranteed, no deps)
  2. Try ML layer (IsolationForest anomaly detection) — gracefully skipped on failure
  3. Cache result for 2 minutes per user (auto-invalidated on data changes)
  4. NEVER raises an exception to the caller

Output format:
    {
        "suggestions": [...],
        "alerts":      [...],
        "tips":        [...],
        "anomalies":   [...],
        "meta": {
            "ml_used": bool,
            "months_analyzed": int,
            "categories_analyzed": int,
            "total_spent": float,
            "total_budgeted": float,
        }
    }
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from django.core.cache import cache

from expenses.services import rule_engine

logger = logging.getLogger(__name__)

_CACHE_TIMEOUT = 120   # 2 minutes — low enough to feel real-time
_LOOKBACK_MONTHS = 6   # how many months of history to analyse


def _cache_key(user) -> str:
    # User-ID based key: ai_budget_<user_id>
    return f'ai_budget_{user.pk}'


def _build_empty_result() -> dict:
    return {
        'suggestions': [],
        'alerts': [],
        'tips': [],
        'anomalies': [],
        'meta': {
            'ml_used': False,
            'months_analyzed': 0,
            'categories_analyzed': 0,
            'total_spent': 0.0,
            'total_budgeted': 0.0,
        },
    }


def _run_ml_layer(user, today: date) -> list[dict]:
    """
    Optional ML layer: IsolationForest to detect anomalous monthly spend
    per category.  Wrapped in try/except — NEVER propagates to caller.

    Returns a list of anomaly alert dicts (may be empty).
    """
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import IsolationForest
    from expenses.models import Expense

    anomalies = []

    # Pull last N months of data
    start = (today.replace(day=1) - timedelta(days=_LOOKBACK_MONTHS * 30))
    rows = Expense.objects.filter(
        user=user,
        date__gte=start,
    ).values('category', 'date', 'amount')

    if not rows:
        return anomalies

    df = pd.DataFrame(rows)
    df['amount'] = df['amount'].astype(float)
    df['month'] = pd.to_datetime(df['date']).dt.to_period('M')

    # Pivot: rows = months, cols = categories
    pivot = (
        df.groupby(['month', 'category'])['amount']
        .sum()
        .unstack(fill_value=0)
    )

    if pivot.shape[0] < 3 or pivot.shape[1] < 1:
        return anomalies  # Not enough data for ML

    # Fit IsolationForest
    clf = IsolationForest(contamination=0.15, random_state=42, n_estimators=50)
    predictions = clf.fit_predict(pivot.values)

    # Check last row (current month)
    current_pred = predictions[-1]
    if current_pred == -1:
        # Identify which categories are unusually high this month
        current_row = pivot.iloc[-1]
        historical_mean = pivot.iloc[:-1].mean()
        big_deviations = current_row[
            (current_row > historical_mean * 1.5) & (current_row > 0)
        ]
        if not big_deviations.empty:
            cats = ', '.join(big_deviations.index.tolist())
            anomalies.append({
                'title': '⚠️ Unusual Spending Detected (AI)',
                'message': (
                    f'This month\'s spending pattern looks unusual compared to your '
                    f'6-month history. Notable categories: {cats}. '
                    f'Review your recent transactions.'
                ),
                'icon': 'bi-robot',
                'severity': 'warning',
            })
        else:
            anomalies.append({
                'title': '⚠️ Spending Anomaly Detected (AI)',
                'message': (
                    'Your overall spending pattern this month is statistically unusual '
                    'compared to your recent history. Consider reviewing your expenses.'
                ),
                'icon': 'bi-robot',
                'severity': 'warning',
            })

    return anomalies


def generate_budget_analysis(user, force_refresh: bool = False) -> dict:
    """
    Main entry point. Returns structured budget analysis for `user`.
    Cached for 2 minutes; invalidated automatically on any data mutation.
    Pass force_refresh=True to bypass cache and recompute immediately.
    Never raises.
    """
    cache_key = _cache_key(user)

    # ── Force refresh: delete stale cache entry ───────────────────────────────
    if force_refresh:
        cache.delete(cache_key)

    # ── Cache hit ─────────────────────────────────────────────────────────────
    cached = cache.get(cache_key)
    if cached is not None:
        cached['meta']['from_cache'] = True
        return cached

    today = date.today()
    result = _build_empty_result()

    try:
        from expenses.models import Budget

        budgets = list(Budget.objects.filter(user=user))
        total_budgeted = sum(b.monthly_budget for b in budgets)

        # ── Rule engine (guaranteed) ──────────────────────────────────────────
        rule_output = rule_engine.analyze(user, budgets, today)
        result['suggestions'] = rule_output.get('suggestions', [])
        result['alerts']      = rule_output.get('alerts', [])
        result['tips']        = rule_output.get('tips', [])

        # ── Meta stats ────────────────────────────────────────────────────────
        from expenses.models import Expense
        from django.db.models import Sum as _Sum

        total_spent_raw = Expense.objects.filter(
            user=user,
            date__year=today.year,
            date__month=today.month,
        ).aggregate(t=_Sum('amount'))['t'] or Decimal('0')

        result['meta'].update({
            'months_analyzed': _LOOKBACK_MONTHS,
            'categories_analyzed': len(budgets),
            'total_spent': float(total_spent_raw),
            'total_budgeted': float(total_budgeted),
            'month': today.strftime('%B %Y'),
        })

        # ── ML layer (optional, wrapped) ──────────────────────────────────────
        try:
            anomalies = _run_ml_layer(user, today)
            result['anomalies'] = anomalies
            result['meta']['ml_used'] = True
        except Exception as ml_exc:
            logger.warning('AI Budget ML layer skipped: %s', ml_exc)
            result['meta']['ml_used'] = False

    except Exception as exc:
        logger.error('AI Budget Engine failed, returning empty result: %s', exc)
        result['alerts'].append({
            'title': 'Analysis Unavailable',
            'message': 'Could not complete the analysis right now. Please try again shortly.',
            'icon': 'bi-exclamation-circle',
            'severity': 'warning',
        })

    # ── Cache result ──────────────────────────────────────────────────────────
    cache.set(cache_key, result, _CACHE_TIMEOUT)
    return result


def invalidate_cache(user) -> None:
    """Call this whenever budget/expense data changes to force fresh analysis."""
    cache.delete(_cache_key(user))
