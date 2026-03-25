"""
rule_engine.py — Rule-based budget analysis engine.

Guaranteed to run with no external dependencies.
Always returns a valid result structure.
"""
from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Sum


def analyze(user, budgets, today=None):
    """
    Analyze user budgets against real expense data and return
    rule-based suggestions, alerts, and tips.

    Returns:
        dict with keys: suggestions, alerts, tips
        Each value is a list of dicts: {title, message, icon, severity}
    """
    if today is None:
        today = date.today()

    from expenses.models import Expense, Income, SavingGoal

    suggestions = []
    alerts = []
    tips = []

    # ── Fetch current month data ──────────────────────────────────────────────
    month_expenses = Expense.objects.filter(
        user=user,
        date__year=today.year,
        date__month=today.month,
    )
    current_by_cat = {}
    for exp in month_expenses:
        current_by_cat[exp.category] = current_by_cat.get(exp.category, Decimal('0')) + exp.amount

    # ── Fetch previous month data for trend analysis ──────────────────────────
    first_of_month = today.replace(day=1)
    prev_month_end = first_of_month - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    prev_expenses = Expense.objects.filter(
        user=user,
        date__gte=prev_month_start,
        date__lte=prev_month_end,
    )
    prev_by_cat = {}
    for exp in prev_expenses:
        prev_by_cat[exp.category] = prev_by_cat.get(exp.category, Decimal('0')) + exp.amount

    # ── Fetch income ──────────────────────────────────────────────────────────
    monthly_income = Income.objects.filter(
        user=user,
        date__year=today.year,
        date__month=today.month,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    total_budget = sum(b.monthly_budget for b in budgets)
    total_spent = sum(current_by_cat.values())

    # ── Rule 1: Per-category budget utilisation ───────────────────────────────
    for budget in budgets:
        cat = budget.category
        spent = current_by_cat.get(cat, Decimal('0'))
        limit = budget.monthly_budget
        if limit <= 0:
            continue
        pct = float(spent / limit) * 100

        if pct > 100:
            alerts.append({
                'title': f'Over Budget: {cat}',
                'message': (
                    f'You have exceeded your {cat} budget by '
                    f'₹{float(spent - limit):.0f} ({pct - 100:.0f}% over). '
                    f'Consider cutting back immediately.'
                ),
                'icon': 'bi-exclamation-triangle-fill',
                'severity': 'danger',
            })
            suggestions.append({
                'title': f'Reduce {cat} Spending',
                'message': (
                    f'Your {cat} budget is ₹{float(limit):.0f}/month. '
                    f'Try reducing by 15–20% next month to stay within limits.'
                ),
                'icon': 'bi-scissors',
                'severity': 'danger',
            })

        elif pct >= 80:
            alerts.append({
                'title': f'High Spending: {cat}',
                'message': (
                    f'{cat} is at {pct:.0f}% of your monthly budget '
                    f'(₹{float(spent):.0f} / ₹{float(limit):.0f}). '
                    f'Slow down to avoid overspending.'
                ),
                'icon': 'bi-exclamation-circle-fill',
                'severity': 'warning',
            })

        elif pct >= 50:
            alerts.append({
                'title': f'Watch {cat} Spending',
                'message': (
                    f'{cat} is at {pct:.0f}% of budget with '
                    f'{today.day} of ~30 days elapsed. Pace yourself.'
                ),
                'icon': 'bi-eye-fill',
                'severity': 'info',
            })

        elif pct < 30 and today.day >= 15:
            tips.append({
                'title': f'{cat} Budget Underused',
                'message': (
                    f'Only {pct:.0f}% of your {cat} budget used this month. '
                    f'Consider reallocating ₹{float(limit * Decimal("0.5")):.0f} to savings or goals.'
                ),
                'icon': 'bi-piggy-bank',
                'severity': 'success',
            })

    # ── Rule 2: Month-over-month trend per category ───────────────────────────
    for cat, curr_amt in current_by_cat.items():
        prev_amt = prev_by_cat.get(cat, Decimal('0'))
        if prev_amt > 0:
            growth = float((curr_amt - prev_amt) / prev_amt) * 100
            if growth >= 30:
                alerts.append({
                    'title': f'{cat} Spending Rising Fast',
                    'message': (
                        f'Your {cat} spending is up {growth:.0f}% vs last month '
                        f'(₹{float(prev_amt):.0f} → ₹{float(curr_amt):.0f}). '
                        f'Review recent transactions.'
                    ),
                    'icon': 'bi-graph-up-arrow',
                    'severity': 'warning',
                })
            elif growth <= -25:
                tips.append({
                    'title': f'Great Savings on {cat}',
                    'message': (
                        f'You reduced {cat} spending by {abs(growth):.0f}% vs last month. '
                        f'Keep it up! Consider moving the savings to your goals.'
                    ),
                    'icon': 'bi-award',
                    'severity': 'success',
                })

    # ── Rule 3: Income vs total budget ────────────────────────────────────────
    if monthly_income > 0 and total_budget > 0:
        budget_to_income = float(total_budget / monthly_income) * 100
        if budget_to_income > 90:
            alerts.append({
                'title': 'Budget Exceeds Income',
                'message': (
                    f'Your total monthly budget (₹{float(total_budget):.0f}) is '
                    f'{budget_to_income:.0f}% of your income (₹{float(monthly_income):.0f}). '
                    f'Leave room for savings and emergencies.'
                ),
                'icon': 'bi-cash-stack',
                'severity': 'danger',
            })
        elif budget_to_income < 60:
            tips.append({
                'title': 'Allocate Remaining Income',
                'message': (
                    f'You have budgeted only {budget_to_income:.0f}% of your income. '
                    f'Consider allocating ₹{float(monthly_income - total_budget):.0f} '
                    f'to savings goals or an emergency fund.'
                ),
                'icon': 'bi-bank',
                'severity': 'info',
            })

    # ── Rule 4: Overall spend vs income ──────────────────────────────────────
    if monthly_income > 0 and total_spent > 0:
        spend_ratio = float(total_spent / monthly_income) * 100
        if spend_ratio > 80:
            alerts.append({
                'title': 'High Monthly Expenditure',
                'message': (
                    f'You have spent ₹{float(total_spent):.0f} which is {spend_ratio:.0f}% '
                    f'of your ₹{float(monthly_income):.0f} income this month. '
                    f'Aim to keep total expenses below 70% to build savings.'
                ),
                'icon': 'bi-lightning-charge-fill',
                'severity': 'danger',
            })
        elif spend_ratio < 40 and today.day >= 20:
            tips.append({
                'title': 'Excellent Spending Discipline',
                'message': (
                    f'You have only spent {spend_ratio:.0f}% of your income this month. '
                    f'Great job! You can allocate the surplus towards savings goals.'
                ),
                'icon': 'bi-trophy',
                'severity': 'success',
            })

    # ── Rule 5: Savings goals progress ───────────────────────────────────────
    try:
        goals = SavingGoal.objects.filter(user=user, is_complete=False)
        for goal in goals:
            if goal.target_amount > 0:
                progress = float(goal.saved_amount / goal.target_amount) * 100
                if progress < 10 and today.day >= 20:
                    tips.append({
                        'title': f'Goal Behind: {goal.title}',
                        'message': (
                            f'"{goal.title}" is only {progress:.0f}% funded. '
                            f'Consider depositing ₹{float(goal.target_amount - goal.saved_amount):.0f} '
                            f'to stay on track.'
                        ),
                        'icon': 'bi-flag',
                        'severity': 'warning',
                    })
    except Exception:
        pass  # Savings goals optional

    # ── No budget categories set ──────────────────────────────────────────────
    if not budgets:
        suggestions.append({
            'title': 'Set Up Budget Categories',
            'message': (
                'You have not set any budget limits yet. '
                'Start by setting monthly budgets for Food, Travel, Shopping, and Bills '
                'to get personalised insights.'
            ),
            'icon': 'bi-gear',
            'severity': 'info',
        })

    # ── No income recorded ────────────────────────────────────────────────────
    if monthly_income == 0:
        tips.append({
            'title': 'Add Your Income',
            'message': (
                'No income recorded for this month. Add your income to unlock '
                'income-to-spending ratio insights and smarter budget suggestions.'
            ),
            'icon': 'bi-wallet2',
            'severity': 'info',
        })

    return {
        'suggestions': suggestions,
        'alerts': alerts,
        'tips': tips,
    }
