import os
import joblib
import numpy as np
from django.db.models import Sum
from django.db.models.functions import TruncMonth

# Disable TF logging to keep console clean
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

try:
    from tensorflow.keras.models import load_model
except ImportError:
    load_model = None

ML_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(ML_DIR, 'saved_models')
MODEL_PATH = os.path.join(MODEL_DIR, 'expense_lstm.h5')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.pkl')

WINDOW_SIZE = 3

# Singleton pattern for fast global loading
class LSTMPredictorEngine:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LSTMPredictorEngine, cls).__new__(cls)
            cls._instance._load_assets()
        return cls._instance
        
    def _load_assets(self):
        self.model = None
        self.scaler = None
        
        try:
            if load_model and os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
                self.model = load_model(MODEL_PATH)
                self.scaler = joblib.load(SCALER_PATH)
                print("[LSTM Engine] Successfully loaded model and scaler globally.")
            else:
                print(f"[LSTM Engine] Assets missing. Required at: {MODEL_PATH} and {SCALER_PATH}")
        except Exception as e:
            print(f"[LSTM Engine Error] Could not load LSTM assets: {e}")

# Initialize globally
lstm_engine = LSTMPredictorEngine()


def predict_next_month(user) -> float | None:
    """
    Predicts the next month's total expense for a given user.
    If Keras/LSTM is unavailable or datasets are < WINDOW_SIZE, it falls back to a Simple Moving Average (SMA).
    """
    try:
        from expenses.models import Expense
        
        # 1. Fetch user's monthly totals safely ignoring timezone shifts
        monthly_totals = (
            Expense.objects.filter(user=user)
            .annotate(month=TruncMonth('date', tzinfo=None))
            .values('month')
            .annotate(total=Sum('amount'))
            .order_by('month')
        )
        
        print("1. Count of monthly_totals:", len(monthly_totals))
        print("2. Exact monthly_totals list:", list(monthly_totals))
        
        if not monthly_totals:
            return None
            
        # 3. Extract purely floats natively avoiding any anomalies
        values = [float(m['total']) for m in monthly_totals if m['total'] is not None]
        print("3. Extracted values list:", values)
        
        # Prepare deterministic SMA fallback
        fallback_values = values[-WINDOW_SIZE:] if values else []
        fallback_avg = sum(fallback_values) / len(fallback_values) if fallback_values else None
            
        if not lstm_engine.model or not lstm_engine.scaler:
            print("Model/Scaler missing, bypassing explicitly to SMA fallback.")
            return fallback_avg
            
        # Verify length accurately 
        if len(values) < WINDOW_SIZE:
            print(f"Total entries < {WINDOW_SIZE}, triggering SMA fallback natively.")
            return fallback_avg
            
        # Slice only exact sequence count chronologically
        sequence = values[-WINDOW_SIZE:]
        
        # Reshape to 2D column array for scaler safely
        data_array = np.array(sequence).reshape(-1, 1)
        
        # Normalize directly
        scaled_data = lstm_engine.scaler.transform(data_array)
        print("4. Scaled values:", scaled_data.flatten().tolist())
        
        # Enforce exact matrix constraints (batch_size=1, time_steps=WINDOW_SIZE, features=1)
        sequence_reshaped = scaled_data.reshape(1, WINDOW_SIZE, 1)
        print("5. Input shape sent to model:", sequence_reshaped.shape)
        
        try:
            # Predict using globally scaled matrix
            prediction_scaled = lstm_engine.model.predict(sequence_reshaped, verbose=0)
            print("6. Raw model output:", prediction_scaled.flatten().tolist())
        except Exception as e:
            print("Prediction error:", e)
            print("Keras natively failed `.predict()`. Falling back to SMA.")
            return fallback_avg
            
        # Inverse transform result back implicitly to monetary figures
        predicted_value = lstm_engine.scaler.inverse_transform(prediction_scaled)[0][0]
        predicted_value = max(0.0, float(predicted_value))
        
        print("7. Inverse transformed value:", predicted_value)
        return predicted_value
        
    except Exception as e:
        print(f"[LSTM Predictor Error] Next month prediction failed: {e}")
        return None
