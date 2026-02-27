import os
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, 'saved_models')
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_PATH = os.path.join(MODEL_DIR, 'anomaly_model.pkl')

def train_model():
    """
    Train an Isolation Forest model to detect anomalous expense amounts.
    Since we don't have real huge user histories for the initial phase,
    we'll synthesize a dataset of 'normal' spending behavior with a few outliers.
    """
    print("Generating synthetic expense training data...")
    
    # 1. Generate Synthetic Data
    # 200 normal transactions between $5 to $200
    import numpy as np
    normal_amounts = np.random.uniform(5.0, 200.0, 200)
    
    # 5 anomalous transactions highly deviated from normal range ($800 to $2000)
    outlier_amounts = np.random.uniform(800.0, 2000.0, 5)
    
    # Combine into a single feature array of shape (n_samples, 1)
    all_amounts = np.concatenate([normal_amounts, outlier_amounts]).reshape(-1, 1)
    
    # 2. Train Isolation Forest
    # Contamination defines the expected proportion of outliers in the data.
    # Adjusting contamination to roughly the ratio of outliers (5 / 205 = ~0.024)
    print("Training Isolation Forest Anomaly Detector...")
    model = IsolationForest(n_estimators=100, contamination=0.03, random_state=42)
    model.fit(all_amounts)
    
    # Quick sanity check: Are the outliers actually detected?
    predictions = model.predict(all_amounts)
    predicted_outliers_count = (predictions == -1).sum()
    print(f"Sanity Check: Model flagged {predicted_outliers_count} anomalous points out of {len(all_amounts)}.")
    
    # 3. Save Model to disk
    print("Saving Anomaly Model to disk...")
    joblib.dump(model, MODEL_PATH)
    print("Anomaly training complete and files saved successfully.")

if __name__ == '__main__':
    train_model()
