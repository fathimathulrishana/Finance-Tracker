"""
Admin views for Phase-1
- User management
- Analytics dashboard
- Report generation
"""

from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import never_cache
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
import csv
import json
from calendar import month_name

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch

from django.core.cache import cache
from django.http import JsonResponse
from .analytics_service import get_monthly_revenue, get_monthly_expense, get_expense_growth, get_user_stats, get_retention_rate
from .utils.admin_insights import get_admin_insights

from .models import Expense, Income


def is_admin(user):
    """Check if user is staff/superuser."""
    return user.is_staff and user.is_superuser


@never_cache
@user_passes_test(is_admin, redirect_field_name=None)
def admin_dashboard(request):
    """Admin dashboard with system-wide analytics (PHASE-1)."""
    # Extra safety check: redirect non-admin users to regular dashboard
    if not (request.user.is_staff and request.user.is_superuser):
        return redirect('dashboard')
    # ============================================
    # GLOBAL TIME FILTER
    # ============================================
    filter_type = request.GET.get('filter', '30')
    today = datetime.now()
    
    if filter_type == '7':
        start_date = today - timedelta(days=7)
    elif filter_type == '30':
        start_date = today - timedelta(days=30)
    elif filter_type == '180':
        start_date = today - timedelta(days=180)
    elif filter_type == '365':
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)

    # APPLY FILTER TO ALL DATA
    expenses = Expense.objects.filter(date__gte=start_date)
    incomes = Income.objects.filter(date__gte=start_date)
    
    # ============================================
    # SYSTEM-WIDE METRICS
    # ============================================
    total_users = User.objects.count()
    total_expenses = expenses.count()
    total_amount = expenses.aggregate(total=Sum('amount'))['total'] or 0
    avg_expense = total_amount / total_expenses if total_expenses > 0 else 0
    
    # Most spent category (system-wide)
    most_spent_category = expenses.values('category').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total').first()
    
    if most_spent_category:
        most_spent = most_spent_category['category']
    else:
        most_spent = 'N/A'
    
    # ============================================
    # CATEGORY-WISE DISTRIBUTION (FILTERED)
    # ============================================
    all_category_data = expenses.values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    category_labels = [row['category'] for row in all_category_data]
    category_values = [float(row['total']) for row in all_category_data]
    
    # ============================================
    # MONTHLY TREND (FILTERED)
    # ============================================
    yearly_data = expenses.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')
    
    trend_labels = [f"{month_name[row['month'].month]}" for row in yearly_data]
    trend_values = [float(row['total']) for row in yearly_data]
    
    # ============================================
    # RECENT 10 EXPENSES (FOR ADMIN REVIEW)
    # ============================================
    recent_expenses = expenses.select_related('user').order_by('-date')[:10]
    
    context = {
        'filter_type': filter_type,
        'expenses': expenses,
        'incomes': incomes,
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
        'insights': get_admin_insights(),
    }
    return render(request, 'admin/admin_dashboard.html', context)


@never_cache
@user_passes_test(is_admin, redirect_field_name=None)
def manage_users(request):
    """Manage all users - view, activate, deactivate, delete."""
    # Extra safety check: redirect non-admin users
    if not (request.user.is_staff and request.user.is_superuser):
        return redirect('dashboard')
    
    users = User.objects.select_related('profile').all().order_by('-date_joined')
    
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


@never_cache
@user_passes_test(is_admin, redirect_field_name=None)
def admin_analytics_data(request):
    """API endpoint for Advanced Analytics Dashboard (JSON)."""
    # Verify permission
    if not (request.user.is_staff and request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    filter_type = request.GET.get('filter', '30')
    today = datetime.now()
    if filter_type == '7':
        start_date = today - timedelta(days=7)
    elif filter_type == '30':
        start_date = today - timedelta(days=30)
    elif filter_type == '180':
        start_date = today - timedelta(days=180)
    elif filter_type == '365':
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)

    cache_key = f"admin_analytics_{filter_type}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)

    data = {
        "revenue": get_monthly_revenue(start_date=start_date),
        "expenses": get_monthly_expense(start_date=start_date),
        "growth": get_expense_growth(start_date=start_date),
        "users": get_user_stats(start_date=start_date),
        "retention": get_retention_rate(start_date=start_date)
    }
    
    # Cache for 5 minutes
    cache.set(cache_key, data, 300)
    return JsonResponse(data)


@never_cache
@user_passes_test(is_admin, redirect_field_name=None)
def reports(request):
    """
    Generate reports - CSV and PDF exports.
    
    PHASE-1 ONLY:
    - CSV export with proper headers
    - PDF export using ReportLab
    - Separate code paths (no mixing)
    """
    # Extra safety check: redirect non-admin users
    if not (request.user.is_staff and request.user.is_superuser):
        return redirect('dashboard')
    
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        
        # Separate paths for CSV and PDF - NO mixing!
        if report_type == 'csv':
            return generate_csv_report(request)
        elif report_type == 'pdf':
            return generate_pdf_report(request)
    
    return render(request, 'admin/reports.html')


def generate_csv_report(request):
    """
    Generate CSV report of all expenses.
    
    Returns:
        HttpResponse with Content-Type: text/csv
        Includes: Date, Username, Category, Amount, Description
    """
    # Fetch all expenses
    expenses = Expense.objects.select_related('user').order_by('-date')
    
    # Create CSV response with correct Content-Type
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="expenses_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Write header row
    writer.writerow(['Date', 'Username', 'Category', 'Amount (INR)', 'Description'])
    
    # Write data rows
    for expense in expenses:
        writer.writerow([
            expense.date.strftime('%Y-%m-%d'),
            expense.user.username,
            expense.category,
            f"₹{expense.amount:.2f}",
            expense.description,
        ])
    
    return response


def generate_pdf_report(request):
    """
    Generate PDF report of all expenses using ReportLab.
    
    Returns:
        HttpResponse with Content-Type: application/pdf
        Includes: Title, Table with User|Category|Amount|Date
    
    IMPORTANT: This does NOT reuse CSV logic - completely separate!
    """
    # Fetch all expenses
    expenses = Expense.objects.select_related('user').order_by('-date')
    
    # Create PDF response with correct Content-Type
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="expenses_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    # Create PDF document
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # ==========================================
    # TITLE
    # ==========================================
    title = Paragraph("<b>Expense Report - All Users</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.3 * inch))
    
    # ==========================================
    # REPORT METADATA
    # ==========================================
    report_info = f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br/>"
    report_info += f"<b>Total Expenses:</b> {expenses.count()}"
    info_paragraph = Paragraph(report_info, styles['Normal'])
    elements.append(info_paragraph)
    elements.append(Spacer(1, 0.4 * inch))
    
    # ==========================================
    # TABLE: User | Category | Amount | Date
    # ==========================================
    # Table header
    data = [['User', 'Category', 'Amount', 'Date']]
    
    # Table data rows
    for expense in expenses:
        data.append([
            expense.user.username,
            expense.category,
            f"₹{expense.amount:.2f}",
            expense.date.strftime('%Y-%m-%d'),
        ])
    
    # Create table with column widths
    table = Table(data, colWidths=[1.5*inch, 1.5*inch, 1.2*inch, 1.5*inch])
    
    # Apply table styling
    table.setStyle(TableStyle([
        # Header row styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),  # Amount column right-aligned
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
    ]))
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    
    return response
