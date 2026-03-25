import json
from decimal import Decimal
from expenses.models import Income, Expense, SavingGoal
from django.db.models import Sum

u = Expense.objects.first().user
exps = list(Expense.objects.filter(user=u).values('amount', 'date', 'category', 'description').order_by('-date'))
incs = list(Income.objects.filter(user=u).values('amount', 'date', 'source').order_by('-date'))

result = {
    'incomes': [{'amount': float(i['amount']), 'date': str(i['date']), 'source': i['source']} for i in incs],
    'expenses': [{'amount': float(e['amount']), 'date': str(e['date']), 'category': e['category']} for e in exps],
}

total_inc = sum(i['amount'] for i in result['incomes'])
total_exp = sum(e['amount'] for e in result['expenses'])

result['total_inc'] = total_inc
result['total_exp'] = total_exp

with open('financial_dump.json', 'w') as f:
    json.dump(result, f, indent=2)

print("Dump complete")
