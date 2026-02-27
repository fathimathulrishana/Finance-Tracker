import os
import django
import numpy as np
import pandas as pd
from datetime import datetime, date
import joblib

# Setup Django Environment for offline script
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_ai.settings') # Assume project name is finance_ai based on folder struct
django.setup()

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from expenses.models import Expense

# ML Imports (imported after django setup just in case)
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_models')
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_PATH = os.path.join(MODEL_DIR, 'expense_lstm.h5')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.pkl')

WINDOW_SIZE = 3

def create_sequences(data, window_size):
    """
    Creates sequences of length `window_size` to predict the next value.
    Example: [1, 2, 3, 4] with window_size=3
    X = [[1, 2, 3]], y = [4]
    """
    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i:(i + window_size)])
        y.append(data[i + window_size])
    return np.array(X), np.array(y)

def train_lstm():
    print("Fetching monthly totals from database...")
    
    # 1. Load monthly totals using Django ORM
    # In a real scenario, this would group per user. For training the initial standalone model, 
    # we'll use all aggregated platform data (or per user if data is huge). 
    # Since this is a standalone model for the prompt, we'll create synthetic monthly totals 
    # if the DB lacks sufficient month sequences to train an LSTM.
    
    monthly_data = (
        Expense.objects.annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    
    totals = [float(item['total']) for item in monthly_data]
    
    # Check if we have enough real DB data. Need at least (window_size + 1) to make 1 sample.
    # LSTMs need much more than 1 sample to actually train. Usually >20-30 points.
    if len(totals) < 24:
        print(f"Not enough months in DB for LSTM training (found {len(totals)}). Generating synthetic monthly sequence...")
        # Generate 3 years of synthetic trending data with seasonality
        np.random.seed(42)
        base = 10000
        totals = []
        for i in range(36):
            # Base + upward trend + random noise
            val = base + (i * 200) + np.random.normal(0, 500)
            totals.append(max(1000, val)) # ensure positive
            
    print(f"Total months of data for training: {len(totals)}")
    
    # Reshape for scaler (samples, features)
    data_array = np.array(totals).reshape(-1, 1)
    
    # 2. Normalize data
    print("Normalizing data with MinMaxScaler...")
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data_array)
    
    # 3. Create sequences
    print(f"Creating sliding window sequences (window={WINDOW_SIZE})...")
    X, y = create_sequences(scaled_data, WINDOW_SIZE)
    
    # LSTM expects input shape: (samples, time_steps, features)
    # Our data is already formatted correctly by create_sequences for univariate (features=1)
    
    # 4. Train LSTM Model
    print("Building and training simple LSTM Sequential model...")
    model = Sequential()
    
    # Architecture: Input (implicitly defined by input_shape) -> LSTM -> Dense -> Output
    model.add(LSTM(50, activation='relu', input_shape=(WINDOW_SIZE, 1)))
    model.add(Dense(1)) # Output layer for predicting 1 value
    
    model.compile(optimizer='adam', loss='mse')
    
    # Train
    model.fit(X, y, epochs=100, batch_size=4, verbose=0)
    print("Model training completed.")
    
    # 5. Save model and scaler
    print(f"Saving model to: {MODEL_PATH}")
    model.save(MODEL_PATH)
    
    print(f"Saving scaler to: {SCALER_PATH}")
    joblib.dump(scaler, SCALER_PATH)
    
    print("Training script finished successfully!")

if __name__ == '__main__':
    train_lstm()
