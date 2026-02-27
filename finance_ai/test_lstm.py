import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_ai.settings')
import django
django.setup()

from django.contrib.auth.models import User
from expenses.ml.predictors.lstm_predictor import predict_next_month

def run_test():
    try:
        user = User.objects.first()
        if user:
            print("Testing for:", user)
            res = predict_next_month(user)
            print("Final returned result:", res)
        else:
            print("No users found")
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    run_test()
