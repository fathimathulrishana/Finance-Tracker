from django.db import models
from django.contrib.auth.models import User


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
	amount = models.FloatField()
	description = models.TextField(blank=True)
	from datetime import date as dt_date
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
