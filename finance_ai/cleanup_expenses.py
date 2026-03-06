import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_ai.settings')
django.setup()

from expenses.models import Expense
from django.db import connection

MAX_AMOUNT = 1000000.00

def cleanup():
    print(f"Starting database cleanup for expenses > {MAX_AMOUNT} ...")
    
    # We must use raw SQL because the old `FloatField` allowed astronomical values
    # (e.g., 1e+20) which cannot be parsed by Django's new `DecimalField` natively,
    # throwing a `decimal.InvalidOperation` when the ORM tries to fetch and instantiate the record.
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM expenses_expense WHERE amount > %s", [MAX_AMOUNT])
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("No oversized expenses found! Database is clean.")
            return
            
        print(f"Found {count} expenses exceeding the strict validation limit. Capping them now...")
        
        cursor.execute("UPDATE expenses_expense SET amount = %s WHERE amount > %s", [MAX_AMOUNT, MAX_AMOUNT])
        
    print(f"Successfully capped {count} historic expenses to {MAX_AMOUNT}.")

if __name__ == '__main__':
    cleanup()
