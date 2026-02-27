import numpy as np
import pandas as pd
from expenses.ml.model_loader import ml_engine
from expenses.ml.keyword_engine import apply_keyword_rules, clean_text

def predict_category(text: str, debug: bool = False) -> str | None:
    """
    Predict expense category using a hybrid approach:
    1. Keyword engine (Rule-based exact matching)
    2. ML model (TF-IDF + Logistic Regression)
    3. Confidence checker (Fallback if uncertainty is high)
    """
    if not text:
        return None
        
    try:
        # Step 1: Clean text
        cleaned = clean_text(text)
        
        # Step 2: Keyword Engine
        rule_match = apply_keyword_rules(cleaned)
        
        if rule_match:
            if debug:
                print("INPUT:", text)
                print("RULE MATCH:", rule_match)
                print("ML PRED: N/A")
                print("CONF: 1.0 (Exact Match)")
            return rule_match
            
        # Step 3: ML Model Prediction
        if not ml_engine.category_model or not ml_engine.vectorizer:
            return None
            
        vectorized_text = ml_engine.vectorizer.transform([cleaned])
        probabilities = ml_engine.category_model.predict_proba(vectorized_text)[0]
        max_prob = np.max(probabilities)
        ml_pred = ml_engine.category_model.classes_[np.argmax(probabilities)]
        
        if debug:
            print("INPUT:", text)
            print("RULE MATCH: None")
            print("ML PRED:", ml_pred)
            print("CONF:", round(max_prob, 4))
        
        # Step 4: Confidence Check
        if max_prob < 0.60:
            return None
            
        return ml_pred
        
    except Exception as e:
        print(f"[ML Predictor Warning] Categorization prediction failed: {e}")
        return None
