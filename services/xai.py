import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg') # Ensure non-interactive plotting
import matplotlib.pyplot as plt
import shap
import lime
import lime.lime_tabular
from services.inference import InferenceService

# Feature name mapping for clinical explanations
FEATURE_LABELS = {
    'age': 'Age',
    'bp': 'Blood Pressure',
    'sg': 'Specific Gravity (Urine Concentration)',
    'al': 'Albumin (Protein in Urine)',
    'su': 'Sugar (Glucose in Urine)',
    'rbc': 'Red Blood Cells in Urine',
    'pc': 'Pus Cells in Urine',
    'pcc': 'Pus Cell Clumps',
    'ba': 'Bacteria in Urine',
    'bgr': 'Blood Glucose Random',
    'bu': 'Blood Urea',
    'sc': 'Serum Creatinine',
    'sod': 'Sodium',
    'pot': 'Potassium',
    'hemo': 'Hemoglobin',
    'pcv': 'Packed Cell Volume (Hematocrit)',
    'wc': 'White Blood Cell Count',
    'rc': 'Red Blood Cell Count',
    'htn': 'Hypertension (High Blood Pressure)',
    'dm': 'Diabetes Mellitus',
    'cad': 'Coronary Artery Disease',
    'appet': 'Appetite',
    'pe': 'Pedal Edema (Feet Swelling)',
    'ane': 'Anemia'
}

class XAIService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(XAIService, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, static_dir=None):
        if self._initialized:
            return
            
        self.inference_service = InferenceService()
        
        if static_dir is None:
            base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            self.static_dir = os.path.join(base_dir, 'static')
        else:
            self.static_dir = static_dir
            
        self.plots_dir = os.path.join(self.static_dir, 'xai_plots')
        os.makedirs(self.plots_dir, exist_ok=True)
        
        # Initialize synthetic background dataset
        self.generate_synthetic_background()
        
        # Pre-generate global plots if they don't exist
        self.generate_global_summary_plot()
        
        self._initialized = True

    def generate_synthetic_background(self):
        """
        Creates a synthetic background dataset based on statistics
        for SHAP KernelExplainer and LIME tabular explainer.
        """
        stats = self.inference_service.stats
        feature_columns = self.inference_service.feature_columns
        encoders = self.inference_service.label_encoders
        
        np.random.seed(42)
        n_samples = 200
        synthetic_data = {}
        
        for col in feature_columns:
            # Check if column is in stats (classification is present too, but we ignore it)
            if col in stats.columns:
                col_mean = float(stats.loc['mean', col])
                col_std = float(stats.loc['std', col])
                col_min = float(stats.loc['min', col])
                col_max = float(stats.loc['max', col])
                
                # Generate values using normal distribution
                vals = np.random.normal(loc=col_mean, scale=col_std, size=n_samples)
                vals = np.clip(vals, col_min, col_max)
                
                # Categorical features need mapping to integer classes
                if col in encoders:
                    vals = np.round(vals).astype(int)
                    n_classes = len(encoders[col].classes_)
                    vals = np.clip(vals, 0, n_classes - 1)
                    
                synthetic_data[col] = vals
            else:
                # Default safety
                synthetic_data[col] = np.zeros(n_samples)
                
        self.synthetic_df = pd.DataFrame(synthetic_data)
        self.scaled_synthetic = self.inference_service.scaler.transform(self.synthetic_df)
        
        # Small background for SHAP speed
        self.shap_background = self.scaled_synthetic[:20]
        
        # Initialize LIME Explainer
        self.lime_explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=self.scaled_synthetic,
            feature_names=feature_columns,
            class_names=['ckd', 'notckd'],
            mode='classification'
        )

    def generate_global_summary_plot(self):
        """
        Pre-generates global SHAP summary plot for the dashboard.
        """
        path = os.path.join(self.plots_dir, "global_summary.png")
        if os.path.exists(path):
            return  # Already generated
            
        try:
            print("Generating Global SHAP Summary Plot...")
            def predict_ckd_proba(x):
                return self.inference_service.model.predict_proba(x)[:, 0]
                
            explainer = shap.KernelExplainer(predict_ckd_proba, self.shap_background)
            
            # Explain 25 samples from synthetic set
            explain_samples = self.scaled_synthetic[:25]
            shap_values = explainer.shap_values(explain_samples)
            
            plt.figure(figsize=(9, 5.5))
            shap.summary_plot(
                shap_values, 
                explain_samples, 
                feature_names=self.inference_service.feature_columns, 
                show=False
            )
            plt.title("Global Feature Importance (SHAP attributions)", fontsize=14, pad=15)
            plt.tight_layout()
            plt.savefig(path, dpi=150)
            plt.close()
            print("Global Summary Plot saved successfully.")
        except Exception as e:
            print(f"Error generating Global Summary Plot: {e}")

    def generate_local_explanations(self, prediction_id, raw_input, scaled_features, encoded_df):
        """
        Generates Waterfall and LIME Plots, plus text explanations for a specific prediction.
        Returns:
            dict containing paths to plots, and explanation texts.
        """
        feature_columns = self.inference_service.feature_columns
        model = self.inference_service.model
        
        # Output paths
        waterfall_filename = f"prediction_{prediction_id}_shap_waterfall.png"
        lime_filename = f"prediction_{prediction_id}_lime_pyplot.png"
        
        waterfall_path = os.path.join(self.plots_dir, waterfall_filename)
        lime_path = os.path.join(self.plots_dir, lime_filename)
        
        results = {
            'shap_waterfall': f"xai_plots/{waterfall_filename}",
            'lime_plot': f"xai_plots/{lime_filename}",
            'doctor_explanation': "",
            'patient_explanation': "",
            'top_contributors': []
        }
        
        # 1. Prediction function for probability of CKD (index 0)
        def predict_ckd_proba(x):
            return model.predict_proba(x)[:, 0]
            
        # 2. Compute SHAP value for local instance
        try:
            explainer = shap.KernelExplainer(predict_ckd_proba, self.shap_background)
            shap_vals = explainer.shap_values(scaled_features)
            
            expected_val = explainer.expected_value
            if isinstance(expected_val, (np.ndarray, list)):
                expected_val = expected_val[0]
                
            # Create shap.Explanation object
            exp = shap.Explanation(
                values=shap_vals[0],
                base_values=expected_val,
                data=encoded_df.iloc[0].values,
                feature_names=feature_columns
            )
            
            # Save waterfall plot
            plt.figure(figsize=(9, 5.5))
            shap.plots.waterfall(exp, max_display=10, show=False)
            plt.title("SHAP Local Contribution (WaterFall)", fontsize=13, pad=12)
            plt.tight_layout()
            plt.savefig(waterfall_path, dpi=150)
            plt.close()
        except Exception as e:
            print(f"SHAP Waterfall generation failed for prediction {prediction_id}: {e}")
            results['shap_waterfall'] = None
            
        # 3. Generate LIME explanations
        lime_exp_list = []
        try:
            exp = self.lime_explainer.explain_instance(
                data_row=scaled_features[0],
                predict_fn=model.predict_proba,
                num_features=10
            )
            
            # Save Lime pyplot image
            fig = exp.as_pyplot_figure()
            plt.title("LIME Local Feature Contribution", fontsize=13, pad=12)
            plt.tight_layout()
            fig.savefig(lime_path, dpi=150)
            plt.close(fig)
            
            # LIME list format: [('feature_expression', weight), ...]
            # We want to translate this list into features
            lime_exp_list = exp.as_list()
        except Exception as e:
            print(f"LIME generation failed for prediction {prediction_id}: {e}")
            results['lime_plot'] = None
            
        # 4. Generate doctor and patient text explanations based on LIME and SHAP
        results['top_contributors'] = lime_exp_list
        results['doctor_explanation'] = self._generate_doctor_text(lime_exp_list, raw_input)
        results['patient_explanation'] = self._generate_patient_text(lime_exp_list, raw_input)
        
        return results

    def _generate_doctor_text(self, lime_list, raw_input):
        """
        Generate technical, clinician-oriented explanation.
        """
        if not lime_list:
            return "Unable to compile explanation due to explanation failure."
            
        positives = []
        negatives = []
        
        for feature_expr, weight in lime_list:
            # Detect which feature is this
            matched_feature = None
            for key in FEATURE_LABELS.keys():
                if key in feature_expr:
                    matched_feature = key
                    break
            
            if matched_feature:
                label = FEATURE_LABELS[matched_feature]
                raw_val = raw_input.get(matched_feature, 'N/A')
                
                # Format explanation clause
                # Positive weights in LIME mean it moves prediction to class 1 (notckd) or class 0 (ckd)
                # Wait! Let's check which way LIME is configured.
                # In LIME, class_names=['ckd', 'notckd'].
                # LIME explains the prediction outcome. By default, lime explains class 1 ('notckd'),
                # but let's confirm.
                # In LimeTabularExplainer, predict_fn returns proba of all classes.
                # LIME usually explains the predicted class or class 1.
                # In our code, class 0 is 'ckd' and class 1 is 'notckd'.
                # A positive weight in LIME increases the probability of 'notckd' (if explaining class 1),
                # or we can look at the sign:
                # Let's see: in our lime pyplot test:
                # `al <= -0.51` has positive weight 0.141. (This means it supports class 1, 'notckd').
                # `rbc > 0.80` has positive weight 0.109. (Supports 'notckd').
                # This means positive LIME weight supports 'notckd' (CKD Negative),
                # and negative LIME weight supports 'ckd' (CKD Positive).
                # Wait! Let's make sure our text is clinically correct:
                # If a feature increases risk of CKD, it drives prediction towards CKD.
                # So, if a patient has high creatinine (e.g. sc = 3.0), is it a CKD positive factor?
                # Yes, high creatinine is a risk factor. In LIME it would have a negative weight
                # (supporting class 0 'ckd') if LIME is explaining class 1 ('notckd').
                # To make this robust, let's write a simple rule based on clinically known directions,
                # or look at the coefficient sign:
                # Let's say:
                # If a weight is negative (supports 'ckd'), it is a RISK INCREASE factor.
                # If a weight is positive (supports 'notckd'), it is a RISK DECREASE (protective) factor.
                # Let's double check if this is consistent. Yes, since 'ckd' is class 0 and 'notckd' is class 1,
                # the weights returned by LIME for class 1 ('notckd') mean:
                # Negative weight -> decreases 'notckd' probability -> increases 'ckd' risk.
                # Positive weight -> increases 'notckd' probability -> decreases 'ckd' risk.
                # So:
                # Negative weight: risk contributor (increases CKD risk).
                # Positive weight: protective contributor (decreases CKD risk).
                # This is mathematically and logically perfect!
                
                clause = f"{label} (value: {raw_val})"
                if weight < 0:
                    positives.append((clause, abs(weight)))
                else:
                    negatives.append((clause, weight))
                    
        # Construct response
        doc_text = "Clinical Analysis: "
        if positives:
            doc_text += "The patient displays several risk indicators that increase Chronic Kidney Disease susceptibility. "
            doc_text += "The primary risk-promoting clinical factor is " + positives[0][0] + ". "
            if len(positives) > 1:
                other_factors = [p[0] for p in positives[1:4]]
                doc_text += "Other significant risk contributors include: " + ", ".join(other_factors) + ". "
        else:
            doc_text += "No prominent risk-promoting clinical factors were detected. "
            
        if negatives:
            doc_text += "Conversely, the primary stabilizing/protective factors are " + negatives[0][0] + ". "
            if len(negatives) > 1:
                other_negatives = [n[0] for n in negatives[1:3]]
                doc_text += "Additional stabilizing markers include: " + ", ".join(other_negatives) + ". "
                
        return doc_text

    def _generate_patient_text(self, lime_list, raw_input):
        """
        Generate patient-friendly, simple language explanation.
        """
        if not lime_list:
            return "We could not compile a patient-friendly explanation at this moment."
            
        positives = []
        negatives = []
        
        # Same logic: negative weights increase CKD risk.
        for feature_expr, weight in lime_list:
            matched_feature = None
            for key in FEATURE_LABELS.keys():
                if key in feature_expr:
                    matched_feature = key
                    break
            
            if matched_feature:
                # Use simplified names for patients
                simple_labels = {
                    'age': 'Age',
                    'bp': 'Blood Pressure',
                    'sg': 'Urine Concentration (Specific Gravity)',
                    'al': 'Urine Protein (Albumin)',
                    'su': 'Urine Sugar',
                    'rbc': 'Red Blood Cells in urine',
                    'pc': 'Pus Cells in urine',
                    'pcc': 'Pus Cell Clumps in urine',
                    'ba': 'Bacteria in urine',
                    'bgr': 'Blood Sugar Level',
                    'bu': 'Blood Urea (kidney waste product)',
                    'sc': 'Creatinine Level (key kidney marker)',
                    'sod': 'Sodium Level',
                    'pot': 'Potassium Level',
                    'hemo': 'Hemoglobin (oxygen-carrying protein)',
                    'pcv': 'Hematocrit (blood thickness)',
                    'wc': 'White Blood Cell Count',
                    'rc': 'Red Blood Cell Count',
                    'htn': 'High Blood Pressure history',
                    'dm': 'Diabetes history',
                    'cad': 'Heart Disease history',
                    'appet': 'Appetite Quality',
                    'pe': 'Swelling in ankles/legs (Pedal Edema)',
                    'ane': 'Anemia (low blood count)'
                }
                label = simple_labels.get(matched_feature, FEATURE_LABELS[matched_feature])
                raw_val = raw_input.get(matched_feature, 'N/A')
                
                # Check formatting of values to be human readable
                if str(raw_val).lower() == 'normal':
                    val_desc = "normal"
                elif str(raw_val).lower() == 'abnormal':
                    val_desc = "abnormal"
                elif str(raw_val).lower() == 'present':
                    val_desc = "present"
                elif str(raw_val).lower() == 'notpresent':
                    val_desc = "absent"
                elif str(raw_val).lower() == 'yes':
                    val_desc = "yes"
                elif str(raw_val).lower() == 'no':
                    val_desc = "no"
                elif str(raw_val).lower() == 'good':
                    val_desc = "good"
                elif str(raw_val).lower() == 'poor':
                    val_desc = "poor"
                else:
                    val_desc = f"{raw_val}"
                    
                clause = f"{label} of {val_desc}"
                if weight < 0:
                    positives.append(clause)
                else:
                    negatives.append(clause)
                    
        patient_text = "Understanding Your Results: "
        if positives:
            patient_text += "Based on our AI clinical evaluation, the main factor contributing to your kidney risk score is having a " + positives[0] + ". "
            if len(positives) > 1:
                patient_text += "Other parameters that support this finding are having a " + ", ".join(positives[1:3]) + ". "
        else:
            patient_text += "Your laboratory tests are mostly within typical, healthy ranges for kidney function indicators. "
            
        if negatives:
            patient_text += "On the positive side, factors that help reduce your kidney risk include having a " + negatives[0] + ". "
            
        patient_text += "Please review the recommended actions below and consult your doctor to discuss these indicators."
        
        return patient_text
