from django.db import models
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
