from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Sum, Count
from expenses.models import Expense
from django.contrib.auth.models import User

def get_admin_insights():
    today = now()
    insights = []

    try:
        # -----------------------------
        # 1. High Spending Category
        # -----------------------------
        top_category = (
            Expense.objects
            .values('category')
            .annotate(total=Sum('amount'))
            .order_by('-total')
            .first()
        )

        if top_category:
            insights.append({
                'type': 'warning',
                'icon': '⚠',
                'message': f"High spending in {top_category['category']}"
            })
        else:
            insights.append({
                'type': 'info',
                'icon': 'ℹ',
                'message': "No expense data available"
            })

        # -----------------------------
        # 2. Expense Growth
        # -----------------------------
        target_last_month = 12 if today.month == 1 else today.month - 1
        
        current_month = Expense.objects.filter(date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0
        last_month = Expense.objects.filter(date__month=target_last_month).aggregate(total=Sum('amount'))['total'] or 0

        if last_month > 0:
            change = ((current_month - last_month) / last_month) * 100
            if change > 20:
                insights.append({
                    'type': 'danger',
                    'icon': '🔥',
                    'message': f"Expenses increased by {round(change,1)}%"
                })
            else:
                insights.append({
                    'type': 'success',
                    'icon': '✅',
                    'message': f"Expenses stable ({round(change,1)}%)"
                })
        else:
            insights.append({
                'type': 'info',
                'icon': 'ℹ',
                'message': "Not enough data for growth analysis"
            })

        # -----------------------------
        # 3. Inactive Users
        # -----------------------------
        inactive_users = User.objects.filter(last_login__lt=today - timedelta(days=7)).count()

        if inactive_users > 0:
            insights.append({
                'type': 'warning',
                'icon': '👤',
                'message': f"{inactive_users} inactive users detected"
            })
        else:
            insights.append({
                'type': 'success',
                'icon': '✅',
                'message': "All users are active"
            })

    except Exception as e:
        insights.append({
            'type': 'danger',
            'icon': '❌',
            'message': f"Error loading insights"
        })

    return insights
