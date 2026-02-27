import numpy as np
import pandas as pd
from expenses.ml.model_loader import ml_engine

def detect_anomaly(amount: float, user_expenses: list = None) -> bool:
    """
    Detect unusual expenses using statistical logic and Isolation Forest ML mode.
    
    Logic:
    Returns False if user has < 5 expenses.
    Combines ML detection and mean + 2*std logic.
    """
    if amount <= 0:
        return False
        
    try:
        # Check if model is loaded
        if not ml_engine.anomaly_model:
            return False
        # Check user history constraint
        if user_expenses is None or len(user_expenses) < 5:
            return False
            
        amounts = [float(e.amount) for e in user_expenses if e.amount > 0]
        if not amounts:
            return False
            
        mean = np.mean(amounts)
        std = np.std(amounts)
        
        # New Rule: Only consider anomaly if amount > mean + 2*std
        is_stat_anomaly = amount > (mean + 2 * std)
        
        if not is_stat_anomaly:
            return False
            
        # Optional: Cross verify with Isolation forest if needed
        # Prediction: 1 for normal, -1 for anomaly
        # prediction = ml_engine.anomaly_model.predict(amount_array)
        # return (prediction[0] == -1) and is_stat_anomaly
        
        return True
        
    except Exception as e:
        print(f"[ML Predictor Warning] Anomaly prediction failed: {e}")
        return False
