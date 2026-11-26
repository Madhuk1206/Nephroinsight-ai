import pandas as pd
import numpy as np

# Clinical reference limits and metadata
CLINICAL_METADATA = {
    'age': {
        'label': 'Age',
        'unit': 'years',
        'min': 2.0,
        'max': 90.0,
        'default': 50.0,
        'tooltip': 'Age of the patient in years (supported range 2 - 90).'
    },
    'bp': {
        'label': 'Blood Pressure',
        'unit': 'mmHg',
        'min': 50.0,
        'max': 180.0,
        'default': 80.0,
        'tooltip': 'Resting diastolic blood pressure in mmHg.'
    },
    'sg': {
        'label': 'Specific Gravity',
        'unit': '',
        'min': 1.005,
        'max': 1.025,
        'default': 1.020,
        'tooltip': 'Specific gravity of urine, indicating kidney concentration ability. Healthy is usually 1.015 - 1.025.'
    },
    'al': {
        'label': 'Albumin',
        'unit': 'grade (0-5)',
        'min': 0.0,
        'max': 5.0,
        'default': 0.0,
        'tooltip': 'Albumin levels in urine (proteinuria grade 0 to 5, where 0 is normal/absent).'
    },
    'su': {
        'label': 'Sugar',
        'unit': 'grade (0-5)',
        'min': 0.0,
        'max': 5.0,
        'default': 0.0,
        'tooltip': 'Glucose levels in urine (glycosuria grade 0 to 5, where 0 is normal/absent).'
    },
    'rbc': {
        'label': 'Red Blood Cells in Urine',
        'options': ['normal', 'abnormal', 'nan'],
        'default': 'normal',
        'tooltip': 'Presence of red blood cells in urine (hematuria).'
    },
    'pc': {
        'label': 'Pus Cells in Urine',
        'options': ['normal', 'abnormal', 'nan'],
        'default': 'normal',
        'tooltip': 'Presence of pus cells (white blood cells) in urine, indicating infection.'
    },
    'pcc': {
        'label': 'Pus Cell Clumps',
        'options': ['present', 'notpresent', 'nan'],
        'default': 'notpresent',
        'tooltip': 'Clumping of pus cells in urine.'
    },
    'ba': {
        'label': 'Bacteria',
        'options': ['present', 'notpresent', 'nan'],
        'default': 'notpresent',
        'tooltip': 'Detection of bacteria in urine.'
    },
    'bgr': {
        'label': 'Blood Glucose Random',
        'unit': 'mg/dL',
        'min': 20.0,
        'max': 500.0,
        'default': 121.0,
        'tooltip': 'Random blood sugar level in mg/dL (diabetes indicated by values above 200).'
    },
    'bu': {
        'label': 'Blood Urea',
        'unit': 'mg/dL',
        'min': 1.5,
        'max': 400.0,
        'default': 42.0,
        'tooltip': 'Concentration of urea in the blood, indicating filtration performance (healthy is 15-45).'
    },
    'sc': {
        'label': 'Serum Creatinine',
        'unit': 'mg/dL',
        'min': 0.1,
        'max': 80.0,
        'default': 1.2,
        'tooltip': 'Key indicator of kidney function. Measures waste product creatinine in blood (normal is 0.6 - 1.3).'
    },
    'sod': {
        'label': 'Sodium',
        'unit': 'mEq/L',
        'min': 4.5,
        'max': 170.0,
        'default': 138.0,
        'tooltip': 'Sodium concentration in blood (healthy range: 135 - 145).'
    },
    'pot': {
        'label': 'Potassium',
        'unit': 'mEq/L',
        'min': 1.0,
        'max': 50.0,
        'default': 4.4,
        'tooltip': 'Potassium concentration in blood (healthy range: 3.5 - 5.0).'
    },
    'hemo': {
        'label': 'Hemoglobin',
        'unit': 'g/dL',
        'min': 3.0,
        'max': 18.0,
        'default': 12.5,
        'tooltip': 'Hemoglobin level in g/dL. Low values indicate anemia (healthy: 12 - 17.5).'
    },
    'pcv': {
        'label': 'Packed Cell Volume',
        'unit': '%',
        'min': 5.0,
        'max': 55.0,
        'default': 40.0,
        'tooltip': 'Packed cell volume or Hematocrit percentage (healthy: 36% - 50%).'
    },
    'wc': {
        'label': 'White Blood Cell Count',
        'unit': 'cells/cumm',
        'min': 1000.0,
        'max': 30000.0,
        'default': 8000.0,
        'tooltip': 'Total white blood cell count (healthy: 4,000 - 11,000).'
    },
    'rc': {
        'label': 'Red Blood Cell Count',
        'unit': 'million/cmm',
        'min': 1.5,
        'max': 9.0,
        'default': 4.8,
        'tooltip': 'Total red blood cell count (healthy: 4.2 - 5.9).'
    },
    'htn': {
        'label': 'Hypertension',
        'options': ['yes', 'no', 'nan'],
        'default': 'no',
        'tooltip': 'Does the patient suffer from chronic high blood pressure?'
    },
    'dm': {
        'label': 'Diabetes Mellitus',
        'options': ['yes', 'no', 'nan'],
        'default': 'no',
        'tooltip': 'Does the patient have a history of diabetes mellitus?'
    },
    'cad': {
        'label': 'Coronary Artery Disease',
        'options': ['yes', 'no', 'nan'],
        'default': 'no',
        'tooltip': 'Does the patient have coronary artery disease?'
    },
    'appet': {
        'label': 'Appetite',
        'options': ['good', 'poor', 'nan'],
        'default': 'good',
        'tooltip': 'Quality of patient appetite (good or poor).'
    },
    'pe': {
        'label': 'Pedal Edema',
        'options': ['yes', 'no', 'nan'],
        'default': 'no',
        'tooltip': 'Presence of swelling in ankles/feet (fluid retention).'
    },
    'ane': {
        'label': 'Anemia',
        'options': ['yes', 'no', 'nan'],
        'default': 'no',
        'tooltip': 'Is the patient diagnosed with anemia?'
    }
}

def validate_clinical_inputs(form_data):
    """
    Validates form data against expected clinical ranges.
    Returns:
        dict: validated data cleaned and cast to correct types.
        list: list of validation error strings (empty if all valid).
    """
    errors = []
    cleaned_data = {}
    
    for field, meta in CLINICAL_METADATA.items():
        val = form_data.get(field, None)
        
        # Check if missing
        if val is None or val == '':
            cleaned_data[field] = None # Will fall back to default in inference
            continue
            
        if 'options' in meta:
            # Categorical check
            val_str = str(val).lower().strip()
            if val_str not in meta['options']:
                errors.append(f"Invalid value '{val}' for field '{meta['label']}'. Expected: {', '.join(meta['options'])}")
                cleaned_data[field] = meta['default']
            else:
                cleaned_data[field] = val_str
        else:
            # Numerical check
            try:
                val_num = float(val)
                # Range check
                if val_num < meta['min'] or val_num > meta['max']:
                    errors.append(f"Value {val_num} for field '{meta['label']}' is out of clinical bounds ({meta['min']} - {meta['max']} {meta['unit']}).")
                cleaned_data[field] = val_num
            except ValueError:
                errors.append(f"Value '{val}' for field '{meta['label']}' must be a valid number.")
                cleaned_data[field] = meta['default']
                
    return cleaned_data, errors
