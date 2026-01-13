"""
Admin views for Phase-1
- User management
- Expense management
- Analytics dashboard
- Report generation
"""

from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
import csv
import json
from calendar import month_name

from .models import Expense


def is_admin(user):
    """Check if user is staff/superuser."""
    return user.is_staff and user.is_superuser


@user_passes_test(is_admin, redirect_field_name=None)
def admin_dashboard(request):
    """Admin dashboard with system-wide analytics (PHASE-1)."""
    # Extra safety check: redirect non-admin users to regular dashboard
    if not (request.user.is_staff and request.user.is_superuser):
        return redirect('dashboard')
    # ============================================
    # SYSTEM-WIDE METRICS
    # ============================================
    total_users = User.objects.count()
    total_expenses = Expense.objects.count()
    total_amount = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
    avg_expense = total_amount / total_expenses if total_expenses > 0 else 0
    
    # Most spent category (system-wide)
    most_spent_category = Expense.objects.values('category').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total').first()
    
    if most_spent_category:
        most_spent = most_spent_category['category']
    else:
        most_spent = 'N/A'
    
    # ============================================
    # CATEGORY-WISE DISTRIBUTION (ALL TIME)
    # ============================================
    all_category_data = Expense.objects.values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    category_labels = [row['category'] for row in all_category_data]
    category_values = [float(row['total']) for row in all_category_data]
    
    # ============================================
    # MONTHLY TREND (LAST 12 MONTHS)
    # ============================================
    today = datetime.now()
    year_ago = today - timedelta(days=365)
    
    yearly_data = Expense.objects.filter(
        date__gte=year_ago
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')
    
    trend_labels = [f"{month_name[row['month'].month]}" for row in yearly_data]
    trend_values = [float(row['total']) for row in yearly_data]
    
    # ============================================
    # RECENT 10 EXPENSES (FOR ADMIN REVIEW)
    # ============================================
    recent_expenses = Expense.objects.select_related('user').order_by('-date')[:10]
    
    context = {
        # Metrics
        'total_users': total_users,
        'total_expenses': total_expenses,
        'total_amount': f"{total_amount:.2f}",
        'avg_expense': f"{avg_expense:.2f}",
        'most_spent': most_spent,
        # Charts
        'category_labels': json.dumps(category_labels),
        'category_values': json.dumps(category_values),
        'trend_labels': json.dumps(trend_labels),
        'trend_values': json.dumps(trend_values),
        # Recent activity
        'recent_expenses': recent_expenses,
    }
    return render(request, 'admin/admin_dashboard.html', context)


@user_passes_test(is_admin, redirect_field_name=None)
def manage_users(request):
    """Manage all users - view, activate, deactivate, delete."""
    # Extra safety check: redirect non-admin users
    if not (request.user.is_staff and request.user.is_superuser):
        return redirect('dashboard')
    
    users = User.objects.all().order_by('-date_joined')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)
        
        if action == 'deactivate':
            user.is_active = False
            user.save()
            messages.success(request, f"User '{user.username}' deactivated.")
        elif action == 'activate':
            user.is_active = True
            user.save()
            messages.success(request, f"User '{user.username}' activated.")
        elif action == 'delete':
            username = user.username
            user.delete()
            messages.success(request, f"User '{username}' deleted.")
        
        return redirect('admin_manage_users')
    
    context = {'users': users}
    return render(request, 'admin/manage_users.html', context)


@user_passes_test(is_admin, redirect_field_name=None)
def manage_expenses(request):
    """Manage all expenses - view, filter, delete."""
    # Extra safety check: redirect non-admin users
    if not (request.user.is_staff and request.user.is_superuser):
        return redirect('dashboard')
    
    expenses = Expense.objects.select_related('user').order_by('-date')
    
    # Filter by month
    selected_month = request.GET.get('month')
    if selected_month:
        year, month = selected_month.split('-')
        expenses = expenses.filter(date__year=int(year), date__month=int(month))
    
    # Filter by category
    selected_category = request.GET.get('category')
    if selected_category:
        expenses = expenses.filter(category=selected_category)
    
    # Delete expense
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete':
            expense_id = request.POST.get('expense_id')
            expense = get_object_or_404(Expense, id=expense_id)
            expense.delete()
            messages.success(request, "Expense deleted.")
            return redirect('admin_manage_expenses')
    
    categories = Expense.CATEGORY_CHOICES
    context = {
        'expenses': expenses,
        'categories': categories,
        'selected_month': selected_month,
        'selected_category': selected_category,
    }
    return render(request, 'admin/manage_expenses.html', context)


@user_passes_test(is_admin, redirect_field_name=None)
def reports(request):
    """Generate reports - CSV, PDF exports."""
    # Extra safety check: redirect non-admin users
    if not (request.user.is_staff and request.user.is_superuser):
        return redirect('dashboard')
    
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        
        if report_type == 'csv':
            return generate_csv_report()
        elif report_type == 'pdf':
            return generate_pdf_report()
    
    return render(request, 'admin/reports.html')


def generate_csv_report():
    """Generate and download CSV report of all expenses."""
    expenses = Expense.objects.select_related('user').order_by('-date')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="expenses_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Username', 'Category', 'Amount', 'Description'])
    
    for expense in expenses:
        writer.writerow([
            expense.date,
            expense.user.username,
            expense.category,
            expense.amount,
            expense.description,
        ])
    
    return response


def generate_pdf_report():
    """Generate and download PDF report of all expenses."""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.units import inch
        from datetime import datetime
    except ImportError:
        # Fallback to CSV if reportlab not installed
        return generate_csv_report()
    
    expenses = Expense.objects.select_related('user').order_by('-date')
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="expenses_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title = Paragraph("Expense Report - All Users", styles['Heading1'])
    elements.append(title)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Report date
    report_date = Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal'])
    elements.append(report_date)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Data table
    data = [['Date', 'Username', 'Category', 'Amount', 'Description']]
    for expense in expenses:
        data.append([
            str(expense.date),
            expense.user.username,
            expense.category,
            f"${expense.amount:.2f}",
            expense.description[:30],  # Truncate long descriptions
        ])
    
    table = Table(data, colWidths=[1.2*inch, 1.2*inch, 1*inch, 1*inch, 2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    return response
