import os
import pandas as pd
import random
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'dummy_data.csv')

from expenses.ml.keyword_engine import clean_text

def validate_and_generate():
    """
    Validates dataset quality and generates synthetic data if needed.
    """
    print("Validating dataset...")
    if not os.path.exists(DATA_PATH):
        print(f"Error: Dataset not found at {DATA_PATH}")
        return

    df = pd.read_csv(DATA_PATH)
    initial_len = len(df)
    
    print(f"Initial row count: {initial_len}")
    
    # Check balance
    print("\nInitial Category Balance:")
    print(df['category'].value_counts())
    
    # Check for noise and clean it
    df['description'] = df['description'].apply(clean_text)
    
    # Drop empty and duplicates
    df = df[df['description'] != ""]
    df = df.drop_duplicates(subset=['description', 'category'])
    cleaned_len = len(df)
    print(f"\nAfter cleaning and deduplication: {cleaned_len} rows")
    
    if cleaned_len < 1000:
        print("\nDataset has < 1000 rows. Generating synthetic data...")
        df_synthetic = generate_synthetic_data(df)
        
        # Combine original and synthetic
        df_combined = pd.concat([df, df_synthetic], ignore_index=True)
        # Final cleanup
        df_combined['description'] = df_combined['description'].apply(clean_text)
        df_combined = df_combined.drop_duplicates(subset=['description', 'category'])
        
        print(f"\nSynthetic data generated. Final count: {len(df_combined)} rows.")
        print("\nFinal Category Balance:")
        print(df_combined['category'].value_counts())
        
        # Save back to CSV
        df_combined.to_csv(DATA_PATH, index=False)
        print("Dataset successfully updated and saved.")
    else:
        print("Dataset has sufficient rows. Saving cleaned version.")
        df.to_csv(DATA_PATH, index=False)

def generate_synthetic_data(original_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates synthetic data to reach > 500 rows with class balance.
    """
    categories = original_df['category'].unique()
    
    # Expanded keywords mapped to categories
    # The current categories in dummy_data.csv are: Food, Travel, Transport, Shopping, Bills
    keywords = {
        'Food': [
            'pizza', 'burger', 'mcdonalds', 'kfc', 'subway', 'dominos', 'coffee', 'starbucks',
            'lunch', 'dinner', 'breakfast', 'restaurant', 'cafe', 'swiggy', 'zomato', 'ubereats',
            'grocery', 'supermarket', 'snacks', 'bakery', 'ice cream', 'dining', 'food delivery',
            'blinkit', 'zepto', 'instamart', 'fruits', 'vegetables', 'meat', 'dairy','biryani','mandhi'
        ],
        'Travel': [
            'flight', 'hotel', 'airbnb', 'train', 'irctc', 'makemytrip', 'goibibo', 'cleartrip',
            'bus ticket', 'redbus', 'holiday', 'resort', 'vacation', 'trip', 'booking',
            'indigo', 'air india', 'vistara', 'spicejet', 'yatra', 'ola outstation', 'uber intercity'
        ],
        'Transport': [
            'uber', 'ola', 'taxi', 'cab', 'auto', 'rapido', 'metro card', 'bus pass',
            'petrol', 'diesel', 'fuel', 'cng', 'Indian Oil', 'HP Petrol', 'Bharat Petroleum',
            'parking', 'toll', 'fastag', 'car wash', 'bike service', 'scooter rent'
        ],
        'Shopping': [
            'amazon', 'flipkart', 'myntra', 'ajio', 'meesho', 'zara', 'h&m', 'levis',
            'clothes', 'shoes', 'electronics', 'laptop', 'mobile', 'accessories', 'mall',
            'puma', 'nike', 'adidas', 'watch', 'sunglasses', 'gift', 'beauty', 'nykaa'
        ],
        'Bills': [
            'electricity', 'water', 'gas', 'internet', 'wifi', 'broadband', 'act fibernet',
            'jio', 'airtel', 'vi', 'mobile recharge', 'dth', 'tata sky', 'netflix', 'amazon prime',
            'spotify', 'subscription', 'rent', 'maintenance', 'insurance', 'emi', 'loan'
        ]
    }
    
    prefixes = ['monthly', 'weekly', 'paid for', 'ordered', 'online', 'store', 'bill for', 'recharge', 'ticket for', 'trip to']
    suffixes = ['payment', 'charge', 'order', 'purchase', 'bill', 'expense', 'subscription']
    
    synthetic_rows = []
    
    # Target 300 rows per category to easily cross 1000 and ensure balance
    target_per_category = 300
    
    for category in keywords.keys():
        category_keywords = keywords[category]
        count = 0
        while count < target_per_category:
            kw = random.choice(category_keywords)
            # Create variations
            variation_type = random.randint(1, 4)
            if variation_type == 1:
                desc = kw
            elif variation_type == 2:
                desc = f"{random.choice(prefixes)} {kw}"
            elif variation_type == 3:
                desc = f"{kw} {random.choice(suffixes)}"
            else:
                desc = f"{random.choice(prefixes)} {kw} {random.choice(suffixes)}"
            
            synthetic_rows.append({'description': desc, 'category': category})
            count += 1
            
    return pd.DataFrame(synthetic_rows)

if __name__ == "__main__":
    validate_and_generate()
