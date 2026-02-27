import os
import joblib

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, 'saved_models')

CATEGORY_MODEL_PATH = os.path.join(MODEL_DIR, 'category_model.pkl')
VECTORIZER_PATH = os.path.join(MODEL_DIR, 'vectorizer.pkl')
ANOMALY_MODEL_PATH = os.path.join(MODEL_DIR, 'anomaly_model.pkl')

class MLLoader:
    """
    Singleton pattern to ensure Machine Learning models are 
    only loaded into memory once during the Django server lifecycle.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MLLoader, cls).__new__(cls)
            cls._instance._load_models()
        return cls._instance

    def _load_models(self):
        """Internal method to load the joblib models."""
        self.category_model = None
        self.vectorizer = None
        self.anomaly_model = None
        
        try:
            if os.path.exists(CATEGORY_MODEL_PATH):
                self.category_model = joblib.load(CATEGORY_MODEL_PATH)
            if os.path.exists(VECTORIZER_PATH):
                self.vectorizer = joblib.load(VECTORIZER_PATH)
            if os.path.exists(ANOMALY_MODEL_PATH):
                self.anomaly_model = joblib.load(ANOMALY_MODEL_PATH)
                
            print("[ML Loader] Successfully loaded predictive models into memory.")
        except Exception as e:
            print(f"[ML Loader Error] Failed to load models: {e}")

# Expose a global initialized singleton instance
ml_engine = MLLoader()
