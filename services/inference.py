import os
import joblib
import pandas as pd
import numpy as np

class InferenceService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(InferenceService, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, models_dir=None):
        if self._initialized:
            return
            
        if models_dir is None:
            # Look at default models directory
            base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            models_dir = os.path.join(base_dir, 'models')
            if not os.path.exists(models_dir):
                models_dir = os.path.join(base_dir, 'ml_models')
                
        self.models_dir = models_dir
        self.feature_columns = None
        self.label_encoders = None
        self.scaler = None
        self.model = None
        self.stats = None
        
        self.load_artifacts()
        self._initialized = True

    def load_artifacts(self):
        try:
            print(f"Loading ML artifacts from: {self.models_dir}")
            self.feature_columns = joblib.load(os.path.join(self.models_dir, "feature_columns.pkl"))
            self.label_encoders = joblib.load(os.path.join(self.models_dir, "label_encoder.pkl"))
            self.scaler = joblib.load(os.path.join(self.models_dir, "scaler.pkl"))
            self.model = joblib.load(os.path.join(self.models_dir, "hybrid_model.pkl"))
            self.stats = joblib.load(os.path.join(self.models_dir, "dataset_statistics.pkl"))
            print("Successfully loaded all ML artifacts.")
        except Exception as e:
            print(f"CRITICAL ERROR loading ML artifacts: {e}")
            raise e

    def preprocess_and_format(self, raw_input):
        """
        Takes raw dictionary of input values, fills missing values,
        applies label encoding, and reorders features.
        """
        # Create a copy to prevent side effects
        processed = {}

        # 1. Fill and convert variables
        for col in self.feature_columns:
            val = raw_input.get(col, None)
            
            # Check if categorical
            if col in self.label_encoders:
                # If value is None, empty or nan, map to 'nan'
                if val is None or val == '' or str(val).lower() == 'nan':
                    processed[col] = 'nan'
                else:
                    processed[col] = str(val).lower().strip()
            else:
                # Numerical column
                if val is None or val == '':
                    # Impute using median (50% percentile) from stats
                    processed[col] = float(self.stats.loc['50%', col])
                else:
                    try:
                        processed[col] = float(val)
                    except ValueError:
                        # Fallback to median on parse failure
                        processed[col] = float(self.stats.loc['50%', col])

        df = pd.DataFrame([processed])

        # 2. Encode categorical fields using label encoders
        for col, encoder in self.label_encoders.items():
            if col in df.columns:
                val = df[col].iloc[0]
                try:
                    # Transform. If value is not seen, fallback to 'nan' class
                    if val not in encoder.classes_:
                        val = 'nan'
                    encoded_val = encoder.transform([val])[0]
                    df[col] = encoded_val
                except Exception as e:
                    print(f"Error encoding column {col} with value '{val}': {e}")
                    # Fallback to encoding 'nan'
                    try:
                        df[col] = encoder.transform(['nan'])[0]
                    except:
                        df[col] = 0 # absolute fallback

        # 3. Reorder fields matching feature_columns
        df = df[self.feature_columns]
        return df

    def predict(self, raw_input, threshold=0.5):
        """
        Takes raw inputs, preprocesses, scales, and calls model.
        Returns:
            dict containing:
                - outcome: 'CKD Positive' or 'CKD Negative'
                - ckd_risk_probability: float (probability of CKD, class index 0)
                - notckd_probability: float (probability of Not CKD, class index 1)
                - scaled_features: numpy array (1, 24)
                - encoded_df: pandas DataFrame before scaling
        """
        # Preprocess
        df = self.preprocess_and_format(raw_input)
        
        # Scale
        scaled_features = self.scaler.transform(df)
        
        # Get raw probabilities
        # Soft voting predicts probability arrays
        proba = self.model.predict_proba(scaled_features)
        
        # The classes for 'classification' are ['ckd', 'notckd']
        # Thus:
        # index 0 is 'ckd' (CKD Positive)
        # index 1 is 'notckd' (CKD Negative)
        ckd_risk = float(proba[0][0])
        notckd_risk = float(proba[0][1])
        
        # Determine classification outcome based on customizable threshold
        # If ckd probability is >= threshold, predict CKD Positive
        if ckd_risk >= threshold:
            outcome = 'CKD Positive'
        else:
            outcome = 'CKD Negative'
            
        return {
            'outcome': outcome,
            'ckd_risk_probability': ckd_risk,
            'notckd_probability': notckd_risk,
            'scaled_features': scaled_features,
            'encoded_df': df
        }
