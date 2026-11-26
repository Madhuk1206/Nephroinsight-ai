def generate_clinical_recommendations(prediction_outcome, probability, record_data):
    """
    Generates structured clinical recommendations based on predictions and specific biomarkers.
    Returns a dictionary of categorized recommendation items.
    """
    # Categories
    lifestyle = []
    diet = []
    hydration = []
    exercise = []
    clinical = []
    labs = []
    emergency = []
    
    # 1. Prediction Risk level recommendations
    risk_percent = probability * 100
    if prediction_outcome == 'CKD Positive':
        if risk_percent >= 70:
            emergency.append("Urgent: High risk of Chronic Kidney Disease detected. Schedule a comprehensive nephrology evaluation immediately.")
            clinical.append("Priority referral to a nephrologist for clinical staging (CKD Stage 3-5 assessment).")
        else:
            clinical.append("Refer to a nephrologist or clinical specialist for diagnostic confirmation and early staging.")
            lifestyle.append("Maintain a daily health log tracking blood pressure, weight, and blood glucose levels.")
    else:
        if risk_percent >= 30:
            clinical.append("Moderate risk detected. Recommend monitoring renal markers every 3-6 months with a primary care physician.")
            lifestyle.append("Adopt preventive health modifications to reduce renal stress.")
        else:
            lifestyle.append("Maintain regular healthy habits. Re-evaluate renal health during routine annual check-ups.")
            
    # 2. Serum Creatinine (sc) recommendations
    sc = record_data.get('sc')
    if sc is not None:
        if sc > 1.3:
            clinical.append(f"Elevated Serum Creatinine ({sc} mg/dL). Discuss potential initiation of kidney-protective medications (like ACE inhibitors or ARBs) with a physician.")
            labs.append("Order a 24-hour urine collection for Creatinine Clearance or a spot Urine Albumin-to-Creatinine Ratio (UACR).")
            diet.append("Restrict dietary protein intake (0.6 - 0.8 g/kg body weight per day) under dietitian supervision to slow progression.")
            
    # 3. Blood Urea (bu) recommendations
    bu = record_data.get('bu')
    if bu is not None:
        if bu > 45.0:
            labs.append("Re-check Blood Urea Nitrogen (BUN) and serum electrolytes (Sodium, Potassium, Bicarbonate) to monitor metabolic waste accumulation.")
            diet.append("Avoid excess high-nitrogen protein foods (e.g. processed meats, heavy red meat consumption).")
            if not record_data.get('pe') == 'yes':
                hydration.append("Ensure adequate fluid intake (2-2.5 liters daily) to help clear nitrogenous waste, unless fluid-restricted.")

    # 4. Albumin in Urine (al) recommendations
    al = record_data.get('al')
    if al is not None and al >= 1.0:
        clinical.append(f"Significant Albuminuria (Grade {int(al)}) detected. This indicates glomerular filtration barrier leakage.")
        labs.append("Perform a quantitative urine protein electrophoresis or spot protein-to-creatinine ratio (UPCR).")
        diet.append("Adopt a low-sodium diet (< 2,000 mg of sodium daily) to minimize fluid retention and control blood pressure.")

    # 5. Blood Pressure / Hypertension
    bp = record_data.get('bp')
    htn = record_data.get('htn')
    if (bp is not None and bp > 90.0) or htn == 'yes':
        lifestyle.append("Engage in home blood pressure monitoring twice daily (morning and evening). Target BP < 130/80 mmHg.")
        diet.append("Strictly follow the Dietary Approaches to Stop Hypertension (DASH) eating plan (rich in vegetables, low-fat dairy). Limit salt to < 1.5 - 2g/day.")
        clinical.append("Optimize antihypertensive regimen. Standard choices for renal protection include ACE inhibitors or ARBs.")

    # 6. Diabetes Mellitus / Random Blood Glucose
    dm = record_data.get('dm')
    bgr = record_data.get('bgr')
    if dm == 'yes' or (bgr is not None and bgr > 140.0):
        clinical.append("Strict glycemic control is vital. Target HbA1c < 7.0% to prevent diabetic nephropathy progression.")
        labs.append("Order HbA1c test and fasting blood glucose test if not performed in the last 3 months.")
        exercise.append("Aim for at least 150 minutes of moderate-intensity aerobic exercise per week (e.g., brisk walking 30 min, 5 days a week).")
        diet.append("Limit simple carbohydrates, refined sugars, and high-glycemic foods. Control portion sizes of complex carbs.")

    # 7. Hemoglobin / Anemia
    hemo = record_data.get('hemo')
    ane = record_data.get('ane')
    if (hemo is not None and hemo < 12.0) or ane == 'yes':
        labs.append("Perform a complete anemia workup including Serum Iron, Ferritin, Total Iron Binding Capacity (TIBC), and Percent Transferrin Saturation.")
        diet.append("Consume iron-rich foods (e.g., spinach, fortified grains, lean poultry) paired with Vitamin C to enhance absorption.")
        if hemo is not None and hemo < 10.0:
            clinical.append(f"Severe anemia (Hemoglobin {hemo} g/dL). Discuss potential Erythropoiesis-Stimulating Agent (ESA) therapy and iron supplementation with a physician.")

    # 8. Pedal Edema / Swelling
    pe = record_data.get('pe')
    if pe == 'yes':
        lifestyle.append("Elevate lower extremities above heart level while resting. Avoid sitting or standing in one position for long durations.")
        hydration.append("Strict daily fluid tracking. Restrict total fluid intake to 1.5 liters per day, or as specifically directed by your clinical team.")
        emergency.append("Seek immediate emergency care if you experience sudden shortness of breath or chest pain (signs of fluid overload/pulmonary congestion).")
        diet.append("Strictly restrict salt. Avoid canned foods, pickles, processed snacks, and table salt.")

    # Fallback to avoid empty lists
    if not lifestyle:
        lifestyle.append("Follow standard healthy lifestyle guidelines, maintaining physical activity and stress reduction.")
    if not diet:
        diet.append("Maintain a balanced diet rich in fresh vegetables, whole grains, and lean proteins.")
    if not hydration:
        hydration.append("Stay hydrated by drinking water throughout the day. Target 8-10 glasses (approx. 2 liters) unless fluid-restricted.")
    if not exercise:
        exercise.append("Incorporate 30 minutes of light exercise or walking into your daily routine.")
    if not labs:
        labs.append("Schedule routine annual clinical blood chemistry panels (comprehensive metabolic panel).")

    return {
        'risk_percent': round(risk_percent, 2),
        'risk_level': 'High Risk' if risk_percent >= 70 else ('Moderate Risk' if risk_percent >= 30 else 'Low Risk'),
        'lifestyle_advice': lifestyle,
        'diet_suggestions': diet,
        'hydration_advice': hydration,
        'exercise_suggestions': exercise,
        'clinical_followups': clinical,
        'laboratory_tests': labs,
        'emergency_alerts': emergency
    }
