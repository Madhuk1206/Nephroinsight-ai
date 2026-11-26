from flask import Blueprint, render_template
from flask_login import login_required
from datetime import datetime, date
from database import db
from services.db_model import Patient, Prediction, ClinicalRecord
from services.settings_service import SettingsService

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def dashboard():
    # 1. Fetch counts
    total_patients = Patient.query.count()
    total_predictions = Prediction.query.count()
    
    # Patients registered today
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_patients = Patient.query.filter(Patient.created_at >= today_start).count()
    
    # All predictions to calculate averages and distributions
    predictions = Prediction.query.all()
    
    avg_risk = 0.0
    high_risk_cases = 0
    if predictions:
        total_risk = sum(p.risk_probability for p in predictions)
        avg_risk = (total_risk / len(predictions)) * 100
        high_risk_cases = sum(1 for p in predictions if p.risk_probability >= 0.70)
        
    # 2. Risk distribution for charts
    low_risk_count = 0
    mod_risk_count = 0
    high_risk_count = 0
    
    for p in predictions:
        prob = p.risk_probability * 100
        if prob < 30:
            low_risk_count += 1
        elif prob < 70:
            mod_risk_count += 1
        else:
            high_risk_count += 1
            
    # 3. Age distribution
    # Query age from clinical records or compute from Patient DOB
    patients = Patient.query.all()
    age_buckets = {
        'under_30': 0,
        'age_30_45': 0,
        'age_46_60': 0,
        'age_61_75': 0,
        'over_75': 0
    }
    
    current_year = datetime.now().year
    for pat in patients:
        pat_age = current_year - pat.dob.year
        if pat_age < 30:
            age_buckets['under_30'] += 1
        elif pat_age <= 45:
            age_buckets['age_30_45'] += 1
        elif pat_age <= 60:
            age_buckets['age_46_60'] += 1
        elif pat_age <= 75:
            age_buckets['age_61_75'] += 1
        else:
            age_buckets['over_75'] += 1

    # 4. Recent predictions (table)
    recent_predictions = Prediction.query.order_by(Prediction.created_at.desc()).limit(5).all()
    
    # 5. Recent Activities Timeline
    # Combine recent registrations and predictions
    activities = []
    
    recent_patients_reg = Patient.query.order_by(Patient.created_at.desc()).limit(5).all()
    for pat in recent_patients_reg:
        activities.append({
            'type': 'patient_register',
            'title': f"Patient Registered: {pat.name}",
            'desc': f"ID: {pat.patient_id} • Registered as {pat.gender}",
            'time': pat.created_at
        })
        
    for pred in recent_predictions:
        activities.append({
            'type': 'prediction_made',
            'title': f"Risk Predicted for {pred.patient.name}",
            'desc': f"Outcome: {pred.prediction_outcome} ({round(pred.risk_probability*100, 1)}%)",
            'time': pred.created_at
        })
        
    # Sort activities by time descending
    activities.sort(key=lambda x: x['time'], reverse=True)
    activities = activities[:8] # Take top 8
    
    # Global Summary Plot path verification
    # If the summary plot isn't generated, generating it now is caught inside static directory checks
    # Pass metrics and settings
    hospital_name = SettingsService.get_setting('hospital_name')
    doctor_name = SettingsService.get_setting('doctor_name')
    
    # 6. Trends data (counts per day for last 7 days)
    # Simple summary of predictions count
    return render_template(
        'dashboard/index.html',
        total_patients=total_patients,
        total_predictions=total_predictions,
        today_patients=today_patients,
        avg_risk=round(avg_risk, 1),
        high_risk_cases=high_risk_cases,
        recent_predictions=recent_predictions,
        activities=activities,
        risk_dist={
            'low': low_risk_count,
            'mod': mod_risk_count,
            'high': high_risk_count
        },
        age_dist=age_buckets,
        hospital_name=hospital_name,
        doctor_name=doctor_name
    )
