from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.contrib.auth.models import User
from .models import Income, Expense
from datetime import datetime
import calendar

def get_monthly_revenue(user=None, start_date=None):
    qs = Income.objects.all()
    if start_date:
        qs = qs.filter(date__gte=start_date)
    if user:
        qs = qs.filter(user=user)
        
    revenue_data = qs.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')
    
    result = []
    for entry in revenue_data:
        if entry['month']:
            result.append({
                "month": entry['month'].strftime("%b %Y"),
                "total": float(entry['total'] or 0)
            })
    return result

def get_monthly_expense(user=None, start_date=None):
    qs = Expense.objects.all()
    if start_date:
        qs = qs.filter(date__gte=start_date)
    if user:
        qs = qs.filter(user=user)
        
    expense_data = qs.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')
    
    result = []
    for entry in expense_data:
        if entry['month']:
            result.append({
                "month": entry['month'].strftime("%b %Y"),
                "total": float(entry['total'] or 0)
            })
    return result

def get_expense_growth(start_date=None):
    qs = Expense.objects.all()
    if start_date:
        qs = qs.filter(date__gte=start_date)
    qs = qs.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')
    
    monthly_totals = []
    for entry in qs:
        if entry['month']:
            monthly_totals.append({
                "month": entry['month'].strftime("%b %Y"),
                "total": float(entry['total'] or 0)
            })
            
    result = []
    previous_total = None
    for item in monthly_totals:
        current_total = item['total']
        if previous_total is None or previous_total == 0:
            growth = 0
        else:
            growth = ((current_total - previous_total) / previous_total) * 100
        
        result.append({
            "month": item['month'],
            "growth": round(growth, 2)
        })
        previous_total = current_total
        
    return result

def get_user_stats(start_date=None):
    new_users_qs = User.objects.all()
    if start_date:
        new_users_qs = new_users_qs.filter(date_joined__gte=start_date)
    new_users_qs = new_users_qs.annotate(
        month=TruncMonth('date_joined')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    new_users_dict = {}
    for entry in new_users_qs:
        if entry['month']:
            new_users_dict[entry['month'].strftime("%b %Y")] = entry['count']

    active_users_qs = User.objects.filter(last_login__isnull=False)
    if start_date:
        active_users_qs = active_users_qs.filter(last_login__gte=start_date)
    active_users_qs = active_users_qs.annotate(
        month=TruncMonth('last_login')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    active_users_dict = {}
    for entry in active_users_qs:
        if entry['month']:
            active_users_dict[entry['month'].strftime("%b %Y")] = entry['count']
            
    all_months = sorted(list(set(new_users_dict.keys()) | set(active_users_dict.keys())), key=lambda x: datetime.strptime(x, "%b %Y"))
    result = []
    for m in all_months:
        result.append({
            "month": m,
            "new_users": new_users_dict.get(m, 0),
            "active_users": active_users_dict.get(m, 0)
        })
    return result

def get_retention_rate(start_date=None):
    qs = User.objects.all()
    # While start_date logically limits the users we look at, retention rate spans history.
    # To keep it bounded by timeframe as requested:
    if start_date:
        qs = qs.filter(date_joined__gte=start_date)
        
    users = qs
    # Collect months
    months = set()
    for user in users:
        if user.date_joined:
            months.add(user.date_joined.strftime("%b %Y"))
        if user.last_login:
            months.add(user.last_login.strftime("%b %Y"))
    
    sorted_months = sorted(list(months), key=lambda x: datetime.strptime(x, "%b %Y"))
    
    result = []
    for i, month_str in enumerate(sorted_months):
        target_date = datetime.strptime(month_str, "%b %Y")
        
        # previous month users: users who joined before target_date month/year
        prev_users_count = 0
        retained_count = 0
        
        for user in users:
            if not user.date_joined:
                continue
            
            # Simple check, if user joined before current month
            if user.date_joined.year < target_date.year or (user.date_joined.year == target_date.year and user.date_joined.month < target_date.month):
                prev_users_count += 1
                
                # Check if they have activity now or later (proxy for retained this month)
                if user.last_login:
                    if user.last_login.year >= target_date.year and user.last_login.month >= target_date.month:
                        retained_count += 1
                        
        if prev_users_count > 0:
            rate = (retained_count / prev_users_count) * 100
        else:
            rate = 0
            
        result.append({
            "month": month_str,
            "retention": round(rate, 2)
        })
        
    return result
