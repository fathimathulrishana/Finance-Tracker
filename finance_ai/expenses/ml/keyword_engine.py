import re

# Dictionaries for rule-based matching
FOOD_WORDS = [
    "food", "meal", "lunch", "dinner", "breakfast", "biryani", "pizza", "burger",
    "restaurant", "cafe", "coffee", "tea", "snack", "juice", "mandi", "shawarma"
]

SHOPPING_WORDS = [
    "buy", "bought", "purchase", "shopping", "mall", "amazon", "flipkart",
    "clothes", "shirt", "pant", "bag", "shoes", "book", "electronics"
]

TRAVEL_WORDS = [
    "bus", "uber", "ola", "train", "flight", "metro", "taxi", "fuel", "petrol",
    "diesel", "travel", "trip"
]

BILLS_WORDS = [
    "electricity", "water", "internet", "rent", "bill", "recharge", "subscription"
]

TRANSPORT_WORDS = [
    "uber", "ola", "taxi", "cab", "auto", "rapido", "metro card", "bus pass",
    "petrol", "diesel", "fuel", "cng", "parking", "toll", "fastag"
]

# Map dictionaries to exact category names used in the system
CATEGORY_MAPPING = {
    "Food": FOOD_WORDS,
    "Shopping": SHOPPING_WORDS,
    "Travel": TRAVEL_WORDS,
    "Bills": BILLS_WORDS,
    "Transport": TRANSPORT_WORDS
}

def clean_text(text: str) -> str:
    """
    Cleans text by lowercasing, removing punctuation, 
    removing numbers, and stripping spaces.
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = re.sub(r'\d+', '', text)     # Remove numbers
    text = text.strip()
    return " ".join(text.split())       # Remove extra spaces and normalize

def apply_keyword_rules(text: str) -> str | None:
    """
    Checks if any word in the cleaned text matches the keyword dictionaries.
    Returns the category string if found, otherwise None.
    """
    cleaned = clean_text(text)
    words = cleaned.split()
    
    for word in words:
        for category, keywords in CATEGORY_MAPPING.items():
            if word in keywords:
                return category
                
    return None
