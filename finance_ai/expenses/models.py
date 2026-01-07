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
	date = models.DateField(auto_now_add=True)

	class Meta:
		ordering = ['-date', '-id']

	def __str__(self):
		return f"{self.user.username} | {self.category}: {self.amount} on {self.date}"

# Create your models here.
