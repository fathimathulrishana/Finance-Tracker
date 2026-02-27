import csv
from datetime import date, timedelta, datetime
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

	# Phase N: Time Filter System Integration safely
	range_type = request.GET.get('range', 'current')
	start_str = request.GET.get('start_date')
	end_str = request.GET.get('end_date')
	
	start_date, end_date, current_month_label = get_date_range(range_type, start_str, end_str)

	# Execute strict constraints globally replacing all former naive '.year .month' metrics.
	month_expenses = user_expenses.filter(date__gte=start_date, date__lte=end_date)
	total_month = month_expenses.aggregate(total=Sum('amount'))['total'] or 0
	count_month = month_expenses.count()

	# Execute Comparison evaluation safely
	comp_text, comp_color, comp_icon = get_comparison_stats(user_expenses, start_date, end_date, total_month)

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
	trend_labels = [f"{month_name[row['m'].month]}" for row in trend_qs]
	trend_values = [float(row['total']) for row in trend_qs]

	# Current month display via string identifier 
	current_month = current_month_label
	
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
		'current_range': range_type,
		'start_date': start_str or '',
		'end_date': end_str or '',
		'comparison_text': comp_text,
		'comparison_color': comp_color,
		'comparison_icon': comp_icon,
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
