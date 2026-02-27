from django.db.models import Sum

def categorize_expense(description: str) -> str | None:
    """
    Automatically detect category from description text using simple keyword mapping.
    """
    if not description:
        return None
        
    desc_lower = description.lower()
    
    # Keyword to Category Mapping
    category_map = {
        'pizza': 'Food',
        'burger': 'Food',
        'restaurant': 'Food',
        'grocery': 'Food',
        'supermarket': 'Food',
        'coffee': 'Food',
        'zomato': 'Food',
        'swiggy': 'Food',
        
        'uber': 'Travel',
        'ola': 'Travel',
        'flight': 'Travel',
        'train': 'Travel',
        'bus': 'Travel',
        
        'petrol': 'Others', # Or maybe 'Travel', but mapping shows petrol -> Transport. Let's use categories from models.py: Food, Travel, Shopping, Bills, Others
        'diesel': 'Others',
        'fuel': 'Others',
        
        'amazon': 'Shopping',
        'flipkart': 'Shopping',
        'clothes': 'Shopping',
        'shoes': 'Shopping',
        'myntra': 'Shopping',
        
        'electricity': 'Bills',
        'water': 'Bills',
        'wifi': 'Bills',
        'internet': 'Bills',
        'rent': 'Bills',
        'phone': 'Bills',
        'recharge': 'Bills'
    }
    
    # Simple rule-based logic: check if keyword is in description
    for keyword, category in category_map.items():
        if keyword in desc_lower:
            return category
            
    return None

def detect_anomaly(user, amount: float) -> bool:
    """
    Detect unusually high expenses.
    If expense_amount > (user_average * 2) -> returns True
    """
    from expenses.models import Expense
    
    if amount <= 0:
        return False
        
    # Calculate user's average expense
    history = Expense.objects.filter(user=user)
    total_count = history.count()
    
    if total_count == 0:
        return False # No history to compare against
        
    total_spent = history.aggregate(total=Sum('amount'))['total'] or 0
    average_expense = total_spent / total_count
    
    # If standard average is 0, nothing is anomaly
    if average_expense <= 0:
        return False
        
    # Check if amount is unusually high
    if amount > (average_expense * 2):
        return True
        
    return False

def generate_suggestions(user) -> list[str]:
    """
    Provide simple financial advice based on category percentages.
    """
    from expenses.models import Expense
    
    suggestions = []
    
    user_expenses = Expense.objects.filter(user=user)
    total_spent = user_expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    if total_spent <= 0:
        return ["Add more expenses to get smart insights!"]
        
    # Calculate spending per category
    category_totals = user_expenses.values('category').annotate(total=Sum('amount'))
    
    for item in category_totals:
        category = item['category']
        cat_amount = item['total'] or 0
        percentage = (cat_amount / total_spent) * 100
        
        # Apply rule-based logic
        if category == 'Food' and percentage > 40:
            suggestions.append("You are spending too much on food. Consider cooking at home.")
        elif category == 'Shopping' and percentage > 50:
            suggestions.append("Consider reducing shopping expenses to save more. Your shopping is over 50% of your expenses.")
        elif category == 'Travel' and percentage > 30:
            suggestions.append("Your travel expenses are quite high. Explore cheaper transport options if possible.")
        elif category == 'Bills' and percentage > 60:
            suggestions.append("A large portion of your expenses goes to bills. Check for subscriptions you no longer use.")
            
    # As per prompt: Savings < 20% -> "Try to save more this month" 
    # But we don't track income yet. However, we can just throw a generic savings advice if no other bad warnings exist.
    if not suggestions:
        suggestions.append("Great job keeping your expenses balanced! Try to save at least 20% this month.")
    elif len(suggestions) < 3:
        # Add the savings tip anyway
        suggestions.append("Remember the 50/30/20 rule: 50% needs, 30% wants, 20% savings. Try to save more this month.")
        
    return suggestions
