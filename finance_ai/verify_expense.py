import os
import sys
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_ai.settings')
import django
django.setup()

from django.contrib.auth.models import User
from expenses.models import Expense

def run_test():
    user = User.objects.first()
    if not user:
        print("No users available to test.")
        return
        
    past_date = date.today() - timedelta(days=20)
    
    expense = Expense.objects.create(
        user=user,
        category="Food",
        amount=15.00,
        description="Testing Past Date Saves",
        date=past_date
    )
    
    print("Requested custom date:", past_date)
    print("Database saved date:", expense.date)
    
    if expense.date == past_date:
        print("SUCCESS! The system permits custom dates natively.")
    else:
        print("ERROR! Date still overwritten.")
        
    # Clean up test artifact
    expense.delete()

if __name__ == "__main__":
    run_test()
