from datetime import date
from calendar import month_name

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ExpenseForm, MonthFilterForm, RegisterForm
from .models import Expense


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
def dashboard(request):
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
def expense_list(request):
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
def add_expense(request):
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
def delete_expense(request, pk: int):
	expense = get_object_or_404(Expense, pk=pk, user=request.user)
	if request.method == 'POST':
		expense.delete()
		messages.success(request, 'Expense deleted successfully!')
		return redirect('expense_list')
	return render(request, 'confirm_delete.html', {'expense': expense})

# Create your views here.
