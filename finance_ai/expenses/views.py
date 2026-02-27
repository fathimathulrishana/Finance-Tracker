import csv
from datetime import date
from calendar import month_name

from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse, HttpResponseForbidden

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from .forms import ExpenseForm, MonthFilterForm, RegisterForm
from .models import Expense
from .utils.smart_features import categorize_expense, detect_anomaly as rule_based_anomaly, generate_suggestions
from expenses.ml.predictors.lstm_predictor import predict_next_month
from expenses.ml.predictors.category_predictor import predict_category
from expenses.ml.predictors.anomaly_predictor import detect_anomaly as ml_anomaly


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

	month_expenses = user_expenses.filter(date__year=today.year, date__month=today.month)
	total_month = month_expenses.aggregate(total=Sum('amount'))['total'] or 0
	count_month = month_expenses.count()

	category_summary_qs = (
		month_expenses.values('category').annotate(total=Sum('amount')).order_by('category')
	)
	category_labels = [row['category'] for row in category_summary_qs]
	category_values = [float(row['total']) for row in category_summary_qs]

	trend_qs = (
		user_expenses.filter(date__year=today.year)
		.annotate(m=TruncMonth('date'))
		.values('m')
		.annotate(total=Sum('amount'))
		.order_by('m')
	)
	trend_labels = [f"{month_name[row['m'].month]}" for row in trend_qs]
	trend_values = [float(row['total']) for row in trend_qs]

	# Current month display (e.g., "January 2026")
	current_month = f"{month_name[today.month]} {today.year}"
	
	# Phase 2: Smart Financial Suggestions
	smart_suggestions = generate_suggestions(request.user)
	
	# Phase 4: Next Month LSTM Expense Prediction
	next_month_prediction = predict_next_month(request.user)

	context = {
		'total_month': total_month,
		'count_month': count_month,
		'current_month': current_month,
		'category_labels': category_labels,
		'category_values': category_values,
		'trend_labels': trend_labels,
		'trend_values': trend_values,
		'smart_suggestions': smart_suggestions,
		'next_month_prediction': next_month_prediction,
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

	context = {
		'expenses': qs.order_by('-date', '-id'),
		'form': form,
		'selected_month': selected_month,
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
		messages.success(request, 'Expense deleted successfully!')
		return redirect('expense_list')
	return render(request, 'confirm_delete.html', {'expense': expense})

@login_required
@user_passes_test(is_regular_user, redirect_field_name=None)
def download_expenses_csv(request):
	"""Generates and downloads a CSV of the user's expenses securely."""
	if request.user.is_staff or request.user.is_superuser:
		return redirect('admin_dashboard')
		
	# Single-user isolation
	expenses = Expense.objects.filter(user=request.user).order_by('-date', '-id')
	
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
		
	# Single-user isolation
	expenses = Expense.objects.filter(user=request.user).order_by('-date', '-id')
	
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
	
	date_p = Paragraph(f"Generated on: {current_date}", styles['Normal'])
	elements.append(date_p)
	elements.append(Spacer(1, 12))
	
	data = [['Date', 'Category', 'Amount (Rs)', 'Description']]
	total_amount = 0.0
	
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
