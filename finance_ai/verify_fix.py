import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_ai.settings')
django.setup()

import sqlite3
print('=== Final SQLite type audit ===')
conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
tables = [
    ('expenses_income', 'amount'),
    ('expenses_expense', 'amount'),
    ('expenses_savinggoal', 'target_amount'),
    ('expenses_savinggoal', 'saved_amount'),
    ('expenses_bill', 'amount'),
    ('expenses_budget', 'monthly_budget'),
]
any_real = False
for table, col in tables:
    query = "SELECT id, {} , typeof({}) FROM {} WHERE typeof({}) = 'real'".format(col, col, table, col)
    cur.execute(query)
    rows = cur.fetchall()
    for r in rows:
        print('  FLOAT STILL PRESENT: {}.{} id={} val={}'.format(table, col, r[0], r[1]))
        any_real = True
if not any_real:
    print('  All monetary columns stored as INTEGER or TEXT (no floats) -- CLEAN')
conn.close()
print()
print('=== Income table final state ===')
from expenses.models import Income
for inc in Income.objects.all().order_by('pk'):
    print('  id={}, amount={!r}, source={}'.format(inc.pk, inc.amount, inc.source))

print()
print('=== Forms import check ===')
from expenses.forms import IncomeForm, ExpenseForm, SafeDecimalField, SafeMoneyInput
print('  SafeDecimalField imported OK:', SafeDecimalField)
print('  SafeMoneyInput imported OK:', SafeMoneyInput)
f = IncomeForm()
print('  IncomeForm amount widget type:', type(f.fields['amount'].widget).__name__)
f2 = ExpenseForm()
print('  ExpenseForm amount widget type:', type(f2.fields['amount'].widget).__name__)
