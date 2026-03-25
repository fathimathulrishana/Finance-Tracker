from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import date as dt_date


class Expense(models.Model):
	CATEGORY_CHOICES = [
		('Food', 'Food'),
		('Travel', 'Travel'),
		('Shopping', 'Shopping'),
		('Bills', 'Bills'),
		('Others', 'Others'),
	]

	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
	category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
	amount = models.DecimalField(
		max_digits=10, 
		decimal_places=2,
		validators=[
			MinValueValidator(Decimal('0.01')),
			MaxValueValidator(Decimal('1000000.00'))
		]
	)
	description = models.TextField(blank=True)
	date = models.DateField(default=dt_date.today)
	
	# Phase-2 Smart Features Tracking
	is_anomaly = models.BooleanField(default=False)
	is_auto_categorized = models.BooleanField(default=False)
	is_ml_predicted = models.BooleanField(default=False)

	class Meta:
		ordering = ['-date', '-id']

	def __str__(self):
		return f"{self.user.username} | {self.category}: {self.amount} on {self.date}"

# Create your models here.

class Income(models.Model):
    SOURCE_CHOICES = [
        ('Salary', 'Salary'),
        ('Freelance', 'Freelance'),
        ('Business', 'Business'),
        ('Investment', 'Investment'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0.01')),
            MaxValueValidator(Decimal('100000000.00'))
        ]
    )
    description = models.TextField(blank=True)
    date = models.DateField(default=dt_date.today)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.user.username} | {self.source}: {self.amount} on {self.date}"

class SavingGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saving_goals')
    title = models.CharField(max_length=100)
    target_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    saved_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-deadline', '-created_at']

    def __str__(self):
        return f"{self.user.username} | {self.title}: {self.saved_amount}/{self.target_amount}"

    @property
    def progress(self):
        if self.target_amount > 0:
            return round((self.saved_amount / self.target_amount) * 100, 1)
        return 0.0


class Bill(models.Model):
    CATEGORY_CHOICES = [
        ('Rent', 'Rent'),
        ('Utilities', 'Utilities'),
        ('Entertainment', 'Entertainment'),
        ('Subscriptions', 'Subscriptions'),
        ('Transport', 'Transport'),
        ('Insurance', 'Insurance'),
        ('EMI', 'EMI / Loan'),
        ('Food', 'Food'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bills')
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Other')
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0.01')),
            MaxValueValidator(Decimal('10000000.00'))
        ]
    )
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date', '-created_at']

    def __str__(self):
        return f"{self.user.username} | {self.title}: ₹{self.amount} due {self.due_date}"

    @property
    def status(self):
        today = dt_date.today()
        if self.due_date < today:
            return 'Overdue'
        return 'Due'

    @property
    def days_until_due(self):
        today = dt_date.today()
        return (self.due_date - today).days

    @property
    def is_near_due(self):
        """Returns True if bill is due within 3 days."""
        return 0 <= self.days_until_due <= 3


class Budget(models.Model):
    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Travel', 'Travel'),
        ('Shopping', 'Shopping'),
        ('Bills', 'Bills'),
        ('Others', 'Others'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    monthly_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'category')
        ordering = ['category']

    def __str__(self):
        return f"{self.user.username} | {self.category}: ₹{self.monthly_budget}/month"
