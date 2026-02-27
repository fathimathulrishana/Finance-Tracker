import os
import sys

# Add project root to path so we can import django/expenses
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_ai.settings')
import django
django.setup()

from expenses.ml.predictors.category_predictor import predict_category
from expenses.ml.dataset_validator import validate_and_generate
from expenses.ml.train_classifier import train_model

print("--- STEP 1: Validator & Generator ---")
validate_and_generate()

print("\n--- STEP 2: Training ML Model ---")
train_model()

print("\n--- STEP 3: Testing Predictions (Debug Mode = True) ---")
test_phrases = [
    "lunch at midway restaurant",
    "biryani",
    "mandi",
    "shopping for books",
    "bought shoes and bag",
    "coffee with friends",
    "unknown random phrase testing uncertainty"
]

for phrase in test_phrases:
    print("-" * 30)
    category = predict_category(phrase, debug=True)
    print(f"-> FINAL MAPPED CATEGORY: {category}")

print("-" * 30)
print("Testing complete.")
