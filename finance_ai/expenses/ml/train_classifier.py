import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import joblib

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'dummy_data.csv')
MODEL_DIR = os.path.join(BASE_DIR, 'saved_models')

# Create models directory if it doesn't exist
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODEL_DIR, 'category_model.pkl')
VECTORIZER_PATH = os.path.join(MODEL_DIR, 'vectorizer.pkl')

def train_model():
    """
    Load data, train Logistic Regression model using TF-IDF, and save files.
    """
    print("Loading dataset...")
    df = pd.read_csv(DATA_PATH)
    
    # 1. Prepare Features (X) and Labels (y)
    # Apply preprocessing from our new text cleaner
    from expenses.ml.keyword_engine import clean_text
    X = df['description'].apply(clean_text)

    y = df['category']
    
    # 2. Setup TF-IDF Vectorizer
    print("Vectorizing Text Data...")
    vectorizer = TfidfVectorizer(
        stop_words='english', 
        lowercase=True, 
        max_features=5000,
        ngram_range=(1, 2) # Capture phrases like "uber ride"
    )
    
    # Transform text to numerical features
    X_vectorized = vectorizer.fit_transform(X)
    
    # 3. Choose Classifier: Logistic Regression works very well for small text datasets
    print("Training Logistic Regression Classifier...")
    model = LogisticRegression(class_weight='balanced', max_iter=2000)
    
    # Fit the model
    model.fit(X_vectorized, y)
    
    # Simple training accuracy scoring
    accuracy = model.score(X_vectorized, y) * 100
    print(f"Training Accuracy: {accuracy:.2f}%")
    
    # 4. Save Model and Vectorizer to disk inside `models/` directory
    print("Saving Models to disk...")
    joblib.dump(model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    print("Training complete and files saved successfully.")

if __name__ == '__main__':
    train_model()
