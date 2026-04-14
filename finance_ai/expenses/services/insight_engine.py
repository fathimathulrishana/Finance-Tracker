import datetime
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from expenses.models import Expense, Income

def generate_insights(user, start_date=None, end_date=None):
    """
    Analyzes user expenses to generate intelligent financial insights.
    Compares current period spending with the previous period.
    """
    insights = []
    today = timezone.now().date()
    
    # Default to current month if dates aren't provided
    if not start_date or not end_date:
        start_date = today.replace(day=1)
        # Handle December edge case for next month's first day
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - datetime.timedelta(days=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1, day=1) - datetime.timedelta(days=1)
            
    # Calculate previous period dates for comparison
    duration = (end_date - start_date).days + 1
    prev_end_date = start_date - datetime.timedelta(days=1)
    prev_start_date = prev_end_date - datetime.timedelta(days=duration - 1)
    
    # Fetch current and previous period expenses
    current_expenses = Expense.objects.filter(
        user=user, 
        date__gte=start_date, 
        date__lte=end_date
    )
    
    prev_expenses = Expense.objects.filter(
        user=user, 
        date__gte=prev_start_date, 
        date__lte=prev_end_date
    )
    
    # Group by category
    current_by_category = {}
    for exp in current_expenses:
        current_by_category[exp.category] = current_by_category.get(exp.category, 0) + exp.amount
        
    prev_by_category = {}
    for exp in prev_expenses:
        prev_by_category[exp.category] = prev_by_category.get(exp.category, 0) + exp.amount
        
    # Generate Insights
    # 1. High Spending Alerts (Current Month Totals)
    for category, amount in current_by_category.items():
        if amount > 0:
            insights.append({
                'title': f"Spending Update: {category}",
                'message': f"You spent ₹{amount:.2f} on {category} this period.",
                'category': category,
                'type': 'info',
                'timestamp': timezone.now()
            })
            
    # 2. Trend Analysis (Current vs Previous)
    all_categories = set(current_by_category.keys()).union(set(prev_by_category.keys()))
    
    for category in all_categories:
        curr_amt = current_by_category.get(category, 0)
        prev_amt = prev_by_category.get(category, 0)
        
        if prev_amt > 0:
            diff_pct = ((curr_amt - prev_amt) / prev_amt) * 100
            
            if diff_pct >= 20: # Significant increase
                insights.append({
                    'title': f"Increased Spending: {category}",
                    'message': f"Your {category} spending increased by {diff_pct:.0f}% compared to the previous period.",
                    'category': category,
                    'type': 'warning',
                    'timestamp': timezone.now()
                })
            elif diff_pct <= -20: # Significant decrease
                insights.append({
                    'title': f"Saved on: {category}",
                    'message': f"Great job! Your {category} spending decreased by {abs(diff_pct):.0f}% compared to the previous period.",
                    'category': category,
                    'type': 'success',
                    'timestamp': timezone.now()
                })
                
    # Sort insights (success first, then warnings, then info)
    type_priority = {'success': 0, 'warning': 1, 'info': 2}
    insights.sort(key=lambda x: (type_priority.get(x['type'], 3), x['category']))
    
    return insights


def generate_financial_summary(user, start_date=None, end_date=None):
    """
    Generates structured financial insight metrics for dashboard cards.
    Safe against missing income/expense data and division-by-zero.
    """
    today = timezone.now().date()

    if not start_date or not end_date:
        start_date = today.replace(day=1)
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - datetime.timedelta(days=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1, day=1) - datetime.timedelta(days=1)

    incomes = Income.objects.filter(user=user, date__gte=start_date, date__lte=end_date)
    expenses = Expense.objects.filter(user=user, date__gte=start_date, date__lte=end_date)

    total_income = incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    if total_income > 0:
        savings_rate = ((total_income - total_expenses) / total_income) * Decimal('100')
    else:
        savings_rate = Decimal('0.00')

    monthly_surplus = total_income - total_expenses

    top_category_row = (
        expenses.values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
        .first()
    )

    if top_category_row:
        top_category = {
            'name': top_category_row['category'],
            'amount': float(top_category_row['total'] or Decimal('0.00')),
        }
    else:
        top_category = {
            'name': None,
            'amount': 0.0,
        }

    if total_income == 0 and total_expenses == 0:
        data_status = 'no_data'
    elif total_income > 0 and total_expenses == 0:
        data_status = 'income_only'
    elif total_income == 0 and total_expenses > 0:
        data_status = 'expense_only'
    else:
        data_status = 'normal'

    if savings_rate >= 50:
        savings_tone = 'success'
    elif savings_rate >= 20:
        savings_tone = 'warning'
    else:
        savings_tone = 'danger'

    if monthly_surplus > 0:
        surplus_tone = 'success'
    elif monthly_surplus == 0:
        surplus_tone = 'warning'
    else:
        surplus_tone = 'danger'

    if data_status == 'no_data':
        summary_message = 'No financial data available yet'
    elif data_status == 'income_only':
        summary_message = 'Great! No expenses recorded'
    elif data_status == 'expense_only':
        summary_message = 'No income data available'
    else:
        summary_message = ''

    return {
        'savings_rate': float(round(savings_rate, 2)),
        'monthly_surplus': float(round(monthly_surplus, 2)),
        'top_category': top_category,
        'total_income': float(total_income),
        'total_expenses': float(total_expenses),
        'data_status': data_status,
        'summary_message': summary_message,
        'savings_tone': savings_tone,
        'surplus_tone': surplus_tone,
        'period_note': 'Based on selected time period',
    }
