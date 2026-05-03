import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_ai.settings')
django.setup()

import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

# Fix float-stored expense rows by re-writing as text strings
fixes = [(60, '1199.97'), (61, '29.99')]
for row_id, new_val in fixes:
    cur.execute('UPDATE expenses_expense SET amount = ? WHERE id = ?', (new_val, row_id))
    print('Fixed expenses_expense id={} -> {} (now text storage)'.format(row_id, new_val))

conn.commit()

# Verify no more real-type values
tables_cols = [
    ('expenses_income', 'amount'),
    ('expenses_expense', 'amount'),
    ('expenses_savinggoal', 'target_amount'),
    ('expenses_savinggoal', 'saved_amount'),
    ('expenses_bill', 'amount'),
    ('expenses_budget', 'monthly_budget'),
]

print()
print('=== Final float-type scan ===')
any_float = False
for table, col in tables_cols:
    q = "SELECT id, {c}, typeof({c}) FROM {t} WHERE typeof({c}) = 'real'".format(c=col, t=table)
    cur.execute(q)
    rows = cur.fetchall()
    for r in rows:
        print('  STILL FLOAT: {}.{} id={} val={}'.format(table, col, r[0], r[1]))
        any_float = True

if not any_float:
    print('  CLEAN -- all monetary values stored as INTEGER or TEXT')

conn.close()
