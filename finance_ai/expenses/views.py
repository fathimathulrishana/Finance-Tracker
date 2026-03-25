import csv
from datetime import date, timedelta, datetime
from calendar import month_name
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache


# ── AI cache helper ────────────────────────────────────────────────
def _invalidate_ai_cache(user) -> None:
    """Immediately clear the AI budget analysis cache for this user."""
    cache.delete(f'ai_budget_{user.pk}')
from django.contrib.auth.views import LoginView
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse, HttpResponseForbidden

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .forms import (
    ExpenseForm, MonthFilterForm, RegisterForm, IncomeForm, 
    SavingGoalForm, DepositForm, BillForm, BudgetForm,
    UserUpdateForm, ProfileUpdateForm
)
from .models import Expense, Income, SavingGoal, Bill, Budget, Profile
from .utils.smart_features import categorize_expense, detect_anomaly as rule_based_anomaly, generate_suggestions
from expenses.ml.predictors.lstm_predictor import predict_next_month
from expenses.ml.predictors.category_predictor import predict_category
from expenses.ml.predictors.anomaly_predictor import detect_anomaly as ml_anomaly
from expenses.services.insight_engine import generate_insights


def get_date_range(range_type, start_str=None, end_str=None):
	"""Returns safe start_date, end_date, and textual label given a range_type identifier."""
	today = date.today()
	start_date, end_date, label = None, None, ""
	
	if range_type == 'current' or not range_type:
		start_date = today.replace(day=1)
		try: end_date = start_date.replace(month=start_date.month+1, day=1) - timedelta(days=1)
		except ValueError: end_date = start_date.replace(year=start_date.year+1, month=1, day=1) - timedelta(days=1)
		label = f"Current Month ({today.strftime('%b %Y')})"
	elif range_type == 'previous':
		end_date = today.replace(day=1) - timedelta(days=1)
		start_date = end_date.replace(day=1)
		label = f"Previous Month ({start_date.strftime('%b %Y')})"
	elif range_type == '3months':
		end_date = today
		start_date = (today.replace(day=1) - timedelta(days=65)).replace(day=1)
		label = "Last 3 Months"
	elif range_type == '6months':
		end_date = today
		start_date = (today.replace(day=1) - timedelta(days=160)).replace(day=1)
		label = "Last 6 Months"
	elif range_type == 'year':
		start_date = today.replace(month=1, day=1)
		end_date = today.replace(month=12, day=31)
		label = f"This Year ({today.year})"
	elif range_type == 'custom' and start_str and end_str:
		try:
			start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
			end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
			label = f"Custom ({start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')})"
		except ValueError: pass 
	
	# Ultimate fallback securely defaulting securely to current execution boundaries 
	if not start_date or not end_date:
		start_date = today.replace(day=1)
		try: end_date = start_date.replace(month=start_date.month+1, day=1) - timedelta(days=1)
		except ValueError: end_date = start_date.replace(year=start_date.year+1, month=1, day=1) - timedelta(days=1)
		label = f"Current Month ({today.strftime('%b %Y')})"
		
	return start_date, end_date, label

def get_comparison_stats(user_expenses, start_date, end_date, current_total):
	"""Evaluates explicitly identical previous duration natively predicting offset % changes securely."""
	duration = (end_date - start_date).days + 1
	prev_end_date = start_date - timedelta(days=1)
	prev_start_date = prev_end_date - timedelta(days=duration - 1)
	
	prev_expenses = user_expenses.filter(date__gte=prev_start_date, date__lte=prev_end_date)
	prev_total = prev_expenses.aggregate(total=Sum('amount'))['total'] or 0
	
	if prev_total > 0:
		diff = current_total - prev_total
		percentage = (diff / prev_total) * 100
		if diff > 0: return f"Increased by {percentage:.1f}% vs previous period", "danger", "up"
		elif diff < 0: return f"Decreased by {abs(percentage):.1f}% vs previous period", "success", "down"
		else: return "No change vs previous period", "secondary", "dash"
	else:
		if current_total > 0: return "100% higher than previous period", "danger", "up"
		return "No data in previous period", "secondary", "dash"

def is_regular_user(user):
	"""Check if user is a regular user (not admin/staff)."""
	return not (user.is_staff or user.is_superuser)


class CustomLoginView(LoginView):
	"""
	Custom login view that redirects based on user role.
	
	- Admin users (is_staff OR is_superuser) → /admin-panel/
	- Regular users → / (dashboard)
	"""
	template_name = 'login.html'
	
	def get_success_url(self):
		"""
		Determine redirect URL based on user role after successful login.
		"""
		# Check if user is admin (staff or superuser)
		if self.request.user.is_staff or self.request.user.is_superuser:
			# Redirect admin users to admin dashboard
			return '/admin-panel/'
		else:
			# Redirect regular users to user dashboard (root path)
			return '/'


def register(request):
	if request.method == 'POST':
		form = RegisterForm(request.POST)
		if form.is_valid():
			user = form.save()
			login(request, user)
			messages.success(request, 'Account created successfully!')
			return redirect('dashboard')
		messages.error(request, 'Please correct the errors below.')
	else:
		form = RegisterForm()
	return render(request, 'register.html', {"form": form})


@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def dashboard(request):
	"""User dashboard - restricted to regular users only."""
	# If admin tries to access, they're redirected to admin dashboard
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')
	
	today = date.today()
	user_expenses = Expense.objects.filter(user=request.user)
	user_incomes = Income.objects.filter(user=request.user)

	# Phase N: Time Filter System Integration safely
	range_type = request.GET.get('range', 'current')
	start_str = request.GET.get('start_date')
	end_str = request.GET.get('end_date')
	
	start_date, end_date, current_month_label = get_date_range(range_type, start_str, end_str)

	from datetime import datetime
	if range_type == "current" or not range_type:
		period_label = datetime.now().strftime("%B %Y")
	elif range_type == "previous":
		previous_month = datetime.now().month - 1 or 12
		year = datetime.now().year if datetime.now().month > 1 else datetime.now().year - 1
		period_label = datetime(year, previous_month, 1).strftime("%B %Y")
	elif start_date and end_date:
		period_label = f"{start_date.strftime('%b %Y')} – {end_date.strftime('%b %Y')}"
	else:
		period_label = "All Time"

	# Execute strict constraints globally manually syncing logic for robust insights.
	month_expenses = user_expenses.filter(date__gte=start_date, date__lte=end_date)
	monthly_expenses = month_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	total_month = monthly_expenses
	count_month = month_expenses.count()

	month_incomes = user_incomes.filter(date__gte=start_date, date__lte=end_date)
	monthly_income = month_incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

	all_time_expense = user_expenses.filter(date__lte=end_date).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	all_time_income = user_incomes.filter(date__lte=end_date).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	total_balance = all_time_income - all_time_expense

	# B) Global Data (for Lifetime Savings)
	total_income_all = Income.objects.filter(user=request.user).aggregate(total=Sum('amount'))['total'] or 0
	total_expense_all = Expense.objects.filter(user=request.user).aggregate(total=Sum('amount'))['total'] or 0
	lifetime_savings = total_income_all - total_expense_all
	
	# C) Global Data (for Available Balance calculations previously)
	total_saved_goals = SavingGoal.objects.filter(user=request.user).aggregate(total=Sum('saved_amount'))['total'] or Decimal('0.00')
	net_worth = lifetime_savings

	# MONTH-TO-MONTH COMPARISON
	duration = (end_date - start_date).days + 1
	prev_end_date = start_date - timedelta(days=1)
	prev_start_date = prev_end_date - timedelta(days=duration - 1)

	prev_month_expenses = user_expenses.filter(date__gte=prev_start_date, date__lte=prev_end_date)
	prev_monthly_expense = prev_month_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

	prev_month_incomes = user_incomes.filter(date__gte=prev_start_date, date__lte=prev_end_date)
	prev_monthly_income = prev_month_incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

	prev_all_time_expense = user_expenses.filter(date__lte=prev_end_date).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	prev_all_time_income = user_incomes.filter(date__lte=prev_end_date).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	prev_total_balance = prev_all_time_income - prev_all_time_expense

	prev_savings = Decimal('0.00')

	def get_percent_dict(current, previous):
		if previous and previous > 0:
			pct = ((current - previous) / previous) * 100
			if pct > 0:
				return {'color': "success", 'icon': "bi bi-arrow-up-right", 'text': f"+{abs(pct):.1f}%"}
			elif pct < 0:
				return {'color': "danger", 'icon': "bi bi-arrow-down-right", 'text': f"-{abs(pct):.1f}%"}
			else:
				return {'color': "secondary", 'icon': "bi bi-dash", 'text': "0%"}
		else:
			if current > 0:
				return {'color': "success", 'icon': "bi bi-graph-up-arrow", 'text': "New"}
			elif current < 0:
				return {'color': "danger", 'icon': "bi bi-graph-down-arrow", 'text': "New"}
			else:
				return {'color': "secondary", 'icon': "bi bi-dash", 'text': "Missing"}

	balance_trend = get_percent_dict(total_balance, prev_total_balance)
	income_trend = get_percent_dict(monthly_income, prev_monthly_income)
	expense_trend = get_percent_dict(monthly_expenses, prev_monthly_expense)
	savings_trend = get_percent_dict(lifetime_savings, prev_savings)

	if monthly_income > 0:
		monthly_savings = monthly_income - monthly_expenses
		raw_score = (float(monthly_savings) / float(monthly_income)) * 100
	else:
		raw_score = 0.0

	health_score_val = max(min(raw_score, 100.0), 0.0)
	health_score_display = round(health_score_val, 1)
	
	# Clean integer formatting if no decimals needed
	if float(health_score_display).is_integer():
		health_score_display = int(health_score_display)

	if health_score_val >= 70:
		health_status = "Good"
		health_color = "success"
	elif health_score_val >= 40:
		health_status = "Average"
		health_color = "warning"
	else:
		health_status = "Poor"
		health_color = "danger"

	# Execute Comparison evaluation safely
	comp_text, comp_color, comp_icon = get_comparison_stats(user_expenses, start_date, end_date, total_month)
	comp_text_inc, comp_color_inc, comp_icon_inc = get_comparison_stats(user_incomes, start_date, end_date, monthly_income)

	category_summary_qs = (
		month_expenses.values('category').annotate(total=Sum('amount')).order_by('category')
	)
	category_labels = [row['category'] for row in category_summary_qs]
	category_values = [float(row['total']) for row in category_summary_qs]

	trend_qs = (
		month_expenses.annotate(m=TruncMonth('date', tzinfo=None))
		.values('m')
		.annotate(total=Sum('amount'))
		.order_by('m')
	)
	income_trend_qs = (
		month_incomes.annotate(m=TruncMonth('date', tzinfo=None))
		.values('m')
		.annotate(total=Sum('amount'))
		.order_by('m')
	)

	trend_dict = {}
	for row in trend_qs:
		month_key = f"{month_name[row['m'].month]} {row['m'].year}"
		trend_dict[month_key] = {'expense': float(row['total']), 'income': 0.0, 'm': row['m']}

	for row in income_trend_qs:
		month_key = f"{month_name[row['m'].month]} {row['m'].year}"
		if month_key not in trend_dict:
			trend_dict[month_key] = {'expense': 0.0, 'income': float(row['total']), 'm': row['m']}
		else:
			trend_dict[month_key]['income'] = float(row['total'])

	sorted_months = sorted(trend_dict.values(), key=lambda x: x['m'])
	trend_labels = [f"{month_name[row['m'].month]}" for row in sorted_months]
	trend_values = [row['expense'] for row in sorted_months]
	income_trend_values = [row['income'] for row in sorted_months]

	# Current month display via string identifier 
	current_month = current_month_label
	
	# Phase 2: Smart Financial Suggestions
	smart_suggestions = generate_suggestions(request.user)
	
	# Phase 4: Next Month LSTM Expense Prediction
	next_month_prediction = predict_next_month(request.user)

	# Phase 5: Saving Goals and AI Insights
	saving_goals = SavingGoal.objects.filter(user=request.user)
	insights = generate_insights(request.user, start_date=start_date, end_date=end_date)

	# Upcoming Bills: overdue + due within 30 days, max 5 for dashboard widget
	upcoming_bills = Bill.objects.filter(
		user=request.user,
		is_paid=False,
		due_date__lte=today + timedelta(days=30)
	).order_by('due_date')[:5]

	# Budget teaser: enrich all budgets, surface warning/danger for dashboard
	budgets_qs = Budget.objects.filter(user=request.user)
	budget_enriched = _enrich_budgets(budgets_qs, request.user, today)
	budget_alerts = [e for e in budget_enriched if e['status'] in ('warning', 'danger')][:3]
	budget_set = len(budget_enriched) > 0

	context = {
		'total_month': total_month,
		'count_month': count_month,
		'monthly_income': monthly_income,
		'monthly_expenses': monthly_expenses,
		'total_balance': total_balance,
		'period_label': period_label,
		'lifetime_savings': lifetime_savings,
		'balance_trend': balance_trend,
		'income_trend': income_trend,
		'expense_trend': expense_trend,
		'savings_trend': savings_trend,
		'health_score': health_score_display,
		'health_status': health_status,
		'health_color': health_color,
		'current_month': current_month,
		'category_labels': category_labels,
		'category_values': category_values,
		'trend_labels': trend_labels,
		'trend_values': trend_values,
		'income_trend_values': income_trend_values,
		'smart_suggestions': smart_suggestions,
		'next_month_prediction': next_month_prediction,
		'current_range': range_type,
		'start_date': start_str or '',
		'end_date': end_str or '',
		'comparison_text': comp_text,
		'comparison_color': comp_color,
		'comparison_icon': comp_icon,
		'comparison_text_inc': comp_text_inc,
		'comparison_color_inc': comp_color_inc,
		'comparison_icon_inc': comp_icon_inc,
		'saving_goals': saving_goals,
		'insights': insights,
		'upcoming_bills': upcoming_bills,
		'today': today,
		'budget_alerts': budget_alerts,
		'budget_set': budget_set,
	}
	return render(request, 'dashboard.html', context)


@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def expense_list(request):
	"""User expense list - restricted to regular users only."""
	# If admin tries to access, they're redirected to admin dashboard
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')
	
	form = MonthFilterForm(request.GET or None)
	qs = Expense.objects.filter(user=request.user)

	selected_month = None
	if form.is_valid() and form.cleaned_data.get('month'):
		selected_month = form.cleaned_data['month']
		qs = qs.filter(date__year=selected_month.year, date__month=selected_month.month)

	# 1. Total Expense (over the filtered queryset)
	total_expense = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	
	# 2. This Month / Filtered Month Expense
	today = date.today()
	if selected_month:
		this_month_qs = qs
		month_label = f"Expense ({selected_month.strftime('%b %Y')})"
	else:
		this_month_qs = qs.filter(date__year=today.year, date__month=today.month)
		month_label = "This Month Expense"

	this_month_expense = this_month_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

	# 3. Unique Category Count (unique categories in qs)
	unique_category_count = qs.values('category').distinct().count()

	# 4. Highest Expense Category
	highest_cat_data = qs.values('category').annotate(cat_total=Sum('amount')).order_by('-cat_total').first()
	if highest_cat_data:
		highest_expense_category = f"{highest_cat_data['category']} (₹{highest_cat_data['cat_total']:,.0f})"
	else:
		highest_expense_category = None

	context = {
		'expenses': qs.order_by('-date', '-id'),
		'form': form,
		'selected_month': selected_month,
		'total_expense': total_expense,
		'this_month_expense': this_month_expense,
		'month_label': month_label,
		'unique_category_count': unique_category_count,
		'highest_expense_category': highest_expense_category,
	}
	return render(request, 'expense_list.html', context)


@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def add_expense(request):
	"""Add expense view - restricted to regular users only."""
	# If admin tries to access, they're redirected to admin dashboard
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')
	
	if request.method == 'POST':
		form = ExpenseForm(request.POST)
		if form.is_valid():
			expense = form.save(commit=False)
			expense.user = request.user
			
			# Phase 3: ML Auto Categorization with Phase 2 Fallback
			if not expense.category:
				detected = predict_category(expense.description)
				
				# ML Predicted
				if detected:
					expense.category = detected
					expense.is_auto_categorized = True
					expense.is_ml_predicted = True
				else:
					# Fallback to Phase 2 rule-based keyword mapping
					detected_rule = categorize_expense(expense.description)
					if detected_rule:
						expense.category = detected_rule
						expense.is_auto_categorized = True
						expense.is_ml_predicted = False
					else:
						expense.category = 'Others'  # Default fallback
						expense.is_auto_categorized = False
						expense.is_ml_predicted = False
			else:
				expense.is_auto_categorized = False
				expense.is_ml_predicted = False
				
			# Phase 3: ML Anomaly Detection Filter
			expense.is_anomaly = ml_anomaly(expense.amount)
			if not expense.is_anomaly:
				# Fallback to Phase 2 user-history rule if ML fails or doesn't flag it
				expense.is_anomaly = rule_based_anomaly(request.user, expense.amount)
			
			expense.save()
			_invalidate_ai_cache(request.user)   # ← fresh AI insights after add
			messages.success(request, 'Expense added successfully!')
			return redirect('expense_list')
		messages.error(request, 'Please correct the errors below.')
	else:
		form = ExpenseForm()
	return render(request, 'add_expense.html', {'form': form})


@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def edit_expense(request, pk: int):
	expense = get_object_or_404(Expense, pk=pk, user=request.user)
	if request.method == 'POST':
		form = ExpenseForm(request.POST, instance=expense)
		if form.is_valid():
			expense = form.save(commit=False)
			
			# Phase 3: ML Auto Categorization (evaluate if category set to empty "Auto Detect" by user)
			if not expense.category:
				detected = predict_category(expense.description)
				
				if detected:
					expense.category = detected
					expense.is_auto_categorized = True
					expense.is_ml_predicted = True
				else:
					detected_rule = categorize_expense(expense.description)
					if detected_rule:
						expense.category = detected_rule
						expense.is_auto_categorized = True
						expense.is_ml_predicted = False
					else:
						expense.category = 'Others'
						expense.is_auto_categorized = False
						expense.is_ml_predicted = False
			else:
				# If user explicitly left a category, or changed it from Auto Detected to manual
				expense.is_auto_categorized = False
				expense.is_ml_predicted = False
				
			# Phase 3: ML Anomaly Detection (Re-evaluate anomaly on edit)
			expense.is_anomaly = ml_anomaly(expense.amount)
			if not expense.is_anomaly:
				expense.is_anomaly = rule_based_anomaly(request.user, expense.amount)
			
			expense.save()
			_invalidate_ai_cache(request.user)   # ← fresh AI insights after edit
			messages.success(request, 'Expense updated successfully!')
			return redirect('expense_list')
		messages.error(request, 'Please correct the errors below.')
	else:
		form = ExpenseForm(instance=expense)
	return render(request, 'add_expense.html', {'form': form, 'is_edit': True})


@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def delete_expense(request, pk: int):
	expense = get_object_or_404(Expense, pk=pk, user=request.user)
	if request.method == 'POST':
		expense.delete()
		_invalidate_ai_cache(request.user)   # ← fresh AI insights after delete
		messages.success(request, 'Expense deleted successfully!')
		return redirect('expense_list')
	return render(request, 'confirm_delete.html', {'expense': expense})

@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def income_list(request):
	"""User income list - restricted to regular users only."""
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')
	
	form = MonthFilterForm(request.GET or None)
	qs = Income.objects.filter(user=request.user)

	selected_month = None
	if form.is_valid() and form.cleaned_data.get('month'):
		selected_month = form.cleaned_data['month']
		qs = qs.filter(date__year=selected_month.year, date__month=selected_month.month)

	# 1. Total Income (over the filtered queryset)
	total_income = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	
	# 2. This Month / Filtered Month Income
	today = date.today()
	if selected_month:
		this_month_qs = qs
		month_label = f"Income ({selected_month.strftime('%b %Y')})"
	else:
		this_month_qs = qs.filter(date__year=today.year, date__month=today.month)
		month_label = "This Month Income"

	this_month_income = this_month_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

	# 3. Income Sources Count (unique sources in qs)
	unique_sources_count = qs.values('source').distinct().count()

	# 4. Highest Income Source
	highest_source_data = qs.values('source').annotate(src_total=Sum('amount')).order_by('-src_total').first()
	if highest_source_data:
		highest_income_source = f"{highest_source_data['source']} (₹{highest_source_data['src_total']:,.0f})"
	else:
		highest_income_source = None

	context = {
		'incomes': qs.order_by('-date', '-id'),
		'form': form,
		'selected_month': selected_month,
		'total_income': total_income,
		'this_month_income': this_month_income,
		'month_label': month_label,
		'unique_sources_count': unique_sources_count,
		'highest_income_source': highest_income_source,
	}
	return render(request, 'income_list.html', context)

@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def add_income(request):
	"""Add income view - restricted to regular users only."""
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')
	
	if request.method == 'POST':
		form = IncomeForm(request.POST)
		if form.is_valid():
			income = form.save(commit=False)
			income.user = request.user
			income.save()
			messages.success(request, 'Income added successfully!')
			return redirect('income_list')
		messages.error(request, 'Please correct the errors below.')
	else:
		form = IncomeForm()
	return render(request, 'add_income.html', {'form': form})

@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def edit_income(request, pk: int):
	income = get_object_or_404(Income, pk=pk, user=request.user)
	if request.method == 'POST':
		form = IncomeForm(request.POST, instance=income)
		if form.is_valid():
			form.save()
			messages.success(request, 'Income updated successfully!')
			return redirect('income_list')
		messages.error(request, 'Please correct the errors below.')
	else:
		form = IncomeForm(instance=income)
	return render(request, 'add_income.html', {'form': form, 'is_edit': True})

@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def delete_income(request, pk: int):
	income = get_object_or_404(Income, pk=pk, user=request.user)
	if request.method == 'POST':
		income.delete()
		messages.success(request, 'Income deleted successfully!')
		return redirect('income_list')
	# We can reuse confirm_delete template by returning an object named 'object' or 'item', but currently it relies on 'expense'. 
	# I will pass 'expense' for text matching in template, or I can create a new delete template.
	# Actually, I'll update confirm_delete.html to be generic if needed, but let's just pass 'income' and fix the template context.
	return render(request, 'confirm_delete_income.html', {'income': income})

@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def download_expenses_csv(request):
	"""Generates and downloads a CSV of the user's expenses securely."""
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')
		
	# Filtering
	range_type = request.GET.get('range', 'current')
	start_str = request.GET.get('start_date')
	end_str = request.GET.get('end_date')
	start_date, end_date, _ = get_date_range(range_type, start_str, end_str)

	# Single-user isolation securely constrained	
	expenses = Expense.objects.filter(user=request.user, date__gte=start_date, date__lte=end_date).order_by('-date', '-id')
	
	current_date = date.today().strftime('%Y-%m-%d')
	filename = f"expenses_{request.user.username}_{current_date}.csv"
	
	response = HttpResponse(content_type='text/csv')
	response['Content-Disposition'] = f'attachment; filename="{filename}"'
	
	writer = csv.writer(response)
	writer.writerow(['Date', 'Category', 'Amount', 'Description'])
	
	for expense in expenses:
		writer.writerow([
			expense.date.strftime('%Y-%m-%d'),
			expense.category,
			f"{expense.amount:.2f}",
			expense.description
		])
		
	return response

@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def download_expenses_pdf(request):
	"""Generates and downloads a formatted PDF report securely."""
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')
		
	# Filtering
	range_type = request.GET.get('range', 'current')
	start_str = request.GET.get('start_date')
	end_str = request.GET.get('end_date')
	start_date, end_date, label = get_date_range(range_type, start_str, end_str)

	# Single-user isolation securely constrained
	expenses = Expense.objects.filter(user=request.user, date__gte=start_date, date__lte=end_date).order_by('-date', '-id')
	
	current_date = date.today().strftime('%Y-%m-%d')
	filename = f"expenses_{request.user.username}_{current_date}.pdf"
	
	response = HttpResponse(content_type='application/pdf')
	response['Content-Disposition'] = f'attachment; filename="{filename}"'
	
	# Instantiate reportlab engine
	doc = SimpleDocTemplate(response, pagesize=letter)
	elements = []
	styles = getSampleStyleSheet()
	
	title = Paragraph(f"Expense Report - {request.user.username}", styles['Title'])
	elements.append(title)
	
	filter_context = Paragraph(f"Period: {label}", styles['Normal'])
	elements.append(filter_context)
	
	date_p = Paragraph(f"Report Generated: {current_date}", styles['Normal'])
	elements.append(date_p)
	elements.append(Spacer(1, 12))
	
	data = [['Date', 'Category', 'Amount (Rs)', 'Description']]
	total_amount = Decimal('0.00')
	
	for expense in expenses:
		data.append([
			expense.date.strftime('%Y-%m-%d'),
			expense.category,
			f"{expense.amount:.2f}",
			expense.description[:50] + ('...' if len(expense.description) > 50 else '')
		])
		total_amount += expense.amount
		
	# Total Row 
	data.append(['', 'Total:', f"{total_amount:.2f}", ''])
	
	table = Table(data, colWidths=[80, 100, 80, 240])
	
	style = TableStyle([
		('BACKGROUND', (0, 0), (-1, 0), colors.grey),
		('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
		('ALIGN', (0, 0), (-1, -1), 'LEFT'),
		('ALIGN', (2, 0), (2, -1), 'RIGHT'), # Format amounts matching dashboard layout constraints
		('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
		('FONTSIZE', (0, 0), (-1, 0), 12),
		('BOTTOMPADDING', (0, 0), (-1, 0), 12),
		('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
		('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
		('GRID', (0, 0), (-1, -1), 1, colors.black)
	])
	table.setStyle(style)
	
	elements.append(table)
	doc.build(elements)
	
	return response

@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def add_saving_goal(request):
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')
		
	if request.method == 'POST':
		form = SavingGoalForm(request.POST)
		if form.is_valid():
			goal = form.save(commit=False)
			goal.user = request.user
			goal.save()
			messages.success(request, 'Saving Goal created successfully!')
			return redirect('dashboard')
		messages.error(request, 'Please correct the errors below.')
	else:
		form = SavingGoalForm()
	return render(request, 'add_saving_goal.html', {'form': form})

@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def edit_saving_goal(request, pk: int):
	goal = get_object_or_404(SavingGoal, pk=pk, user=request.user)
	if request.method == 'POST':
		form = SavingGoalForm(request.POST, instance=goal)
		if form.is_valid():
			form.save()
			messages.success(request, 'Saving Goal updated successfully!')
			return redirect('dashboard')
		messages.error(request, 'Please correct the errors below.')
	else:
		form = SavingGoalForm(instance=goal)
	return render(request, 'add_saving_goal.html', {'form': form, 'is_edit': True})

@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def delete_saving_goal(request, pk: int):
	goal = get_object_or_404(SavingGoal, pk=pk, user=request.user)
	if request.method == 'POST':
		goal.delete()
		messages.success(request, 'Saving Goal deleted successfully!')
		return redirect('dashboard')
	return render(request, 'confirm_delete_saving_goal.html', {'goal': goal})

@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def deposit_saving_goal(request, pk: int):
	"""Handle deposits to a saving goal and deduct from available savings."""
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')
		
	goal = get_object_or_404(SavingGoal, pk=pk, user=request.user)
	
	# Calculate user's available savings
	user_expenses = Expense.objects.filter(user=request.user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	user_incomes = Income.objects.filter(user=request.user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
	available_savings = user_incomes - user_expenses
	
	if request.method == 'POST':
		form = DepositForm(request.POST)
		if form.is_valid():
			deposit_amount = Decimal(str(form.cleaned_data['amount']))
			
			if deposit_amount > available_savings:
				messages.error(request, f'Insufficient savings! You only have ₹{available_savings:.2f} available to deposit.')
			else:
				# 1. Add amount to saving goal
				goal.saved_amount += deposit_amount
				goal.save()
				
				# 2. Prevent double counting: Deduct from total balance by creating an Expense 
				Expense.objects.create(
					user=request.user,
					category='Others',
					amount=deposit_amount,
					description=f"Transferred to Saving Goal: {goal.title}"
				)
				
				messages.success(request, f'Successfully deposited ₹{deposit_amount} to {goal.title}!')
				return redirect('dashboard')
		else:
			messages.error(request, 'Please correct the errors below.')
	else:
		form = DepositForm()
		
	return render(request, 'deposit_saving_goal.html', {
		'form': form,
		'goal': goal,
		'available_savings': available_savings
	})

@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def goals_dashboard(request):
	"""Dedicated Goals Dashboard - lists all saving goals with stats."""
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')

	saving_goals = SavingGoal.objects.filter(user=request.user)

	# Summary stats
	total_goals = saving_goals.count()
	completed_goals = sum(1 for g in saving_goals if g.progress >= 100)
	in_progress_goals = total_goals - completed_goals

	total_saved   = saving_goals.aggregate(s=Sum('saved_amount'))['s'] or Decimal('0.00')
	total_target  = saving_goals.aggregate(s=Sum('target_amount'))['s'] or Decimal('0.00')
	overall_pct   = round((total_saved / total_target) * 100, 1) if total_target > 0 else 0.0

	# Available savings (all-time income - all-time expenses - already deposited)
	all_income   = Income.objects.filter(user=request.user).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
	all_expenses = Expense.objects.filter(user=request.user).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
	goal_allocated = saving_goals.aggregate(s=Sum('saved_amount'))['s'] or Decimal('0.00')
	available_savings = max(all_income - all_expenses - goal_allocated, Decimal('0.00'))

	context = {
		'saving_goals': saving_goals,
		'total_goals': total_goals,
		'completed_goals': completed_goals,
		'in_progress_goals': in_progress_goals,
		'total_saved': total_saved,
		'total_target': total_target,
		'overall_pct': overall_pct,
		'available_savings': available_savings,
	}
	return render(request, 'goals_dashboard.html', context)


# ─────────────────────────────────────────────
# UPCOMING BILLS VIEWS
# ─────────────────────────────────────────────

@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def bills_list(request):
	"""Full bills page – shows upcoming + overdue unpaid bills."""
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')

	today = date.today()

	# All unpaid bills for this user ordered by due_date
	bills = Bill.objects.filter(
		user=request.user,
		is_paid=False,
	).order_by('due_date')

	# Stats
	total_bills = Bill.objects.filter(user=request.user, is_paid=False).count()
	overdue_count = sum(1 for b in bills if b.due_date < today)
	near_due_count = sum(1 for b in bills if 0 <= (b.due_date - today).days <= 3)
	total_amount_due = bills.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

	return render(request, 'bills.html', {
		'bills': bills,
		'today': today,
		'total_bills': total_bills,
		'overdue_count': overdue_count,
		'near_due_count': near_due_count,
		'total_amount_due': total_amount_due,
	})


@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def add_bill(request):
	"""Add a new upcoming bill."""
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')

	if request.method == 'POST':
		form = BillForm(request.POST)
		if form.is_valid():
			bill = form.save(commit=False)
			bill.user = request.user
			bill.save()
			messages.success(request, f'Bill "{bill.title}" added successfully!')
			return redirect('bills_list')
		messages.error(request, 'Please correct the errors below.')
	else:
		form = BillForm()
	return render(request, 'add_bill.html', {'form': form})


@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def mark_bill_paid(request, pk):
	"""Mark a bill as paid and auto-create an Expense record."""
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')

	bill = get_object_or_404(Bill, pk=pk, user=request.user)

	if request.method == 'POST':
		if not bill.is_paid:
			bill.is_paid = True
			bill.save()

			# Map bill category to Expense category (best match / fallback)
			expense_category_map = {
				'Rent': 'Bills',
				'Utilities': 'Bills',
				'Entertainment': 'Shopping',
				'Subscriptions': 'Shopping',
				'Transport': 'Travel',
				'Insurance': 'Bills',
				'EMI': 'Bills',
				'Food': 'Food',
				'Other': 'Others',
			}
			expense_cat = expense_category_map.get(bill.category, 'Others')

			# Auto-create expense
			Expense.objects.create(
				user=request.user,
				category=expense_cat,
				amount=bill.amount,
				description=f'Bill Paid: {bill.title}',
				date=date.today(),
			)

			messages.success(request, f'"{bill.title}" marked as paid! Expense of ₹{bill.amount} recorded.')
		else:
			messages.info(request, 'This bill is already marked as paid.')

	next_url = request.POST.get('next', 'bills_list')
	return redirect(next_url)


# ─────────────────────────────────────────────
# BUDGET ALLOCATION VIEWS
# ─────────────────────────────────────────────

_CATEGORY_ICONS = {
	'Food':     'bi-egg-fried',
	'Travel':   'bi-airplane',
	'Shopping': 'bi-bag',
	'Bills':    'bi-receipt',
	'Others':   'bi-grid',
}

_CATEGORY_COLORS = {
	'Food':     '#fb923c',
	'Travel':   '#14b8a6',
	'Shopping': '#8b5cf6',
	'Bills':    '#1e73ff',
	'Others':   '#64748b',
}


def _enrich_budgets(budgets, user, today):
	"""Attach spent_amount, usage_pct and status to each budget object."""
	enriched = []
	for b in budgets:
		spent = Expense.objects.filter(
			user=user,
			category=b.category,
			date__year=today.year,
			date__month=today.month,
		).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

		if b.monthly_budget > 0:
			usage_pct = float(spent / b.monthly_budget) * 100
		else:
			usage_pct = 0.0

		if usage_pct > 100:
			over_percentage = usage_pct - 100
			is_over_budget = True
		else:
			over_percentage = 0
			is_over_budget = False

		if usage_pct >= 80:
			status = 'danger'
		elif usage_pct >= 50:
			status = 'warning'
		else:
			status = 'safe'
			
		# Clean formatting (15.0 -> 15, 15.3 -> 15.3). Capped at 100 display
		capped_usage = min(usage_pct, 100)
		usage_pct_display = int(capped_usage) if capped_usage.is_integer() else round(capped_usage, 1)

		enriched.append({
			'obj': b,
			'spent': spent,
			'usage_pct': min(usage_pct, 100),  # cap bar at 100
			'usage_pct_display': usage_pct_display,
			'is_over_budget': is_over_budget,
			'over_percentage': int(over_percentage) if float(over_percentage).is_integer() else round(over_percentage, 1),
			'status': status,
			'icon': _CATEGORY_ICONS.get(b.category, 'bi-grid'),
			'color': _CATEGORY_COLORS.get(b.category, '#64748b'),
		})
	return enriched


@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def budget_dashboard(request):
	"""Budget Allocation main page."""
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')

	today = date.today()
	budgets = Budget.objects.filter(user=request.user)
	enriched = _enrich_budgets(budgets, request.user, today)

	# Summary stats
	total_categories = len(enriched)
	over_budget_count = sum(1 for e in enriched if e['usage_pct_display'] > 100)
	warning_count = sum(1 for e in enriched if e['status'] == 'warning')
	total_budgeted = budgets.aggregate(t=Sum('monthly_budget'))['t'] or Decimal('0.00')
	total_spent = sum(e['spent'] for e in enriched)

	# Categories not yet budgeted (for Add Budget dropdown pre-filter)
	budgeted_cats = list(budgets.values_list('category', flat=True))
	all_cats = [c[0] for c in Budget.CATEGORY_CHOICES]
	available_cats = [c for c in all_cats if c not in budgeted_cats]

	return render(request, 'budget_dashboard.html', {
		'enriched': enriched,
		'today': today,
		'total_categories': total_categories,
		'over_budget_count': over_budget_count,
		'warning_count': warning_count,
		'total_budgeted': total_budgeted,
		'total_spent': total_spent,
		'available_cats': available_cats,
	})


@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def add_budget(request):
	"""Add a new budget category."""
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')

	if request.method == 'POST':
		form = BudgetForm(request.POST)
		if form.is_valid():
			# Check for duplicate category
			cat = form.cleaned_data['category']
			if Budget.objects.filter(user=request.user, category=cat).exists():
				messages.error(request, f'A budget for "{cat}" already exists. Edit it instead.')
				return render(request, 'add_budget.html', {'form': form})
			budget = form.save(commit=False)
			budget.user = request.user
			budget.save()
			_invalidate_ai_cache(request.user)   # ← clear AI insights cache
			messages.success(request, f'Budget for "{budget.category}" set to ₹{budget.monthly_budget}!')
			return redirect('budget_dashboard')
		messages.error(request, 'Please correct the errors below.')
	else:
		form = BudgetForm()
	return render(request, 'add_budget.html', {'form': form})


@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def edit_budget(request, pk):
	"""Edit monthly budget amount for an existing budget category."""
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')

	budget = get_object_or_404(Budget, pk=pk, user=request.user)
	if request.method == 'POST':
		form = BudgetForm(request.POST, instance=budget)
		if form.is_valid():
			form.save()
			_invalidate_ai_cache(request.user)   # ← clear AI insights cache
			messages.success(request, f'Budget for "{budget.category}" updated!')
			return redirect('budget_dashboard')
		messages.error(request, 'Please correct the errors below.')
	else:
		form = BudgetForm(instance=budget)
	return render(request, 'add_budget.html', {'form': form, 'is_edit': True, 'budget': budget})


@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def delete_budget(request, pk):
	"""Delete a budget category."""
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')

	budget = get_object_or_404(Budget, pk=pk, user=request.user)
	if request.method == 'POST':
		budget.delete()
		_invalidate_ai_cache(request.user)   # ← clear AI insights cache
		messages.success(request, f'Budget for "{budget.category}" removed.')
		return redirect('budget_dashboard')
	return render(request, 'confirm_delete_budget.html', {'budget': budget})


# ─────────────────────────────────────────────────────────────
# AI BUDGET OPTIMIZER VIEW
# ─────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def ai_budget_analysis(request):
	"""
	AJAX endpoint: GET /ai/budget-analysis/
	Returns structured budget analysis as JSON.
	Safe to call multiple times — results cached for 10 minutes.
	"""
	from django.http import JsonResponse
	from expenses.services import ai_budget_engine

	# Check for refresh flag (e.g. ?refresh=true or ?refresh=1)
	force_refresh = request.GET.get('refresh', '').lower() in ['true', '1']

	try:
		result = ai_budget_engine.generate_budget_analysis(request.user, force_refresh=force_refresh)
		return JsonResponse({'status': 'ok', 'data': result})
	except Exception as exc:
		import logging
		logging.getLogger(__name__).error('ai_budget_analysis view error: %s', exc)
		return JsonResponse({
			'status': 'error',
			'data': {
				'suggestions': [],
				'alerts': [{
					'title': 'Analysis Temporarily Unavailable',
					'message': 'Our AI engine is warming up. Please try again in a moment.',
					'icon': 'bi-exclamation-circle',
					'severity': 'warning',
				}],
				'tips': [],
				'anomalies': [],
				'meta': {'ml_used': False, 'months_analyzed': 0,
					'categories_analyzed': 0, 'total_spent': 0, 'total_budgeted': 0},
			}
		}, status=200)  # Always 200 — never crash the UI
@login_required
def profile_view(request):
    """Display the user's profile information."""
    profile = get_object_or_404(Profile, user=request.user)
    return render(request, 'profile.html', {
        'user': request.user,
        'profile': profile
    })

@login_required
def edit_profile(request):
    """Handle user and profile information updates."""
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f'Your account has been updated!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    return render(request, 'profile.html', {
        'u_form': u_form,
        'p_form': p_form,
        'edit_mode': True,
        'profile': request.user.profile
    })

@login_required
def change_password(request):
    """Securely handle user password updates."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important for keeping user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'profile.html', {
        'password_form': form,
        'password_mode': True,
        'profile': request.user.profile
    })
