from datetime import date
from calendar import month_name

from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseForbidden

from .forms import ExpenseForm, MonthFilterForm, RegisterForm
from .models import Expense


def is_regular_user(user):
	"""Check if user is a regular user (not admin/staff)."""
	return not (user.is_staff or user.is_superuser)


class CustomLoginView(LoginView):
	"""
	Custom login view that redirects based on user role.
	
	- Admin users (is_staff OR is_superuser) → /admin-panel/
	- Regular users → /dashboard/
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
			# Redirect regular users to user dashboard
			return '/dashboard/'


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

	context = {
		'total_month': total_month,
		'count_month': count_month,
		'category_labels': category_labels,
		'category_values': category_values,
		'trend_labels': trend_labels,
		'trend_values': trend_values,
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
			form.save()
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

# Create your views here.
