from datetime import datetime
from flask_login import UserMixin
from database import db

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Admin, Doctor, Receptionist
    email = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    predictions = db.relationship('Prediction', backref='predicted_by', lazy=True)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

class Patient(db.Model):
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(30), unique=True, nullable=False) # e.g. NI-2026-0001
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(20), nullable=False) # Male, Female, Other
    contact = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    clinical_records = db.relationship('ClinicalRecord', backref='patient', lazy=True, cascade="all, delete-orphan")
    predictions = db.relationship('Prediction', backref='patient', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Patient {self.name} ({self.patient_id})>"

class ClinicalRecord(db.Model):
    __tablename__ = 'clinical_records'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 24 Clinical Features required by model
    # Numerical features
    age = db.Column(db.Float, nullable=True)
    bp = db.Column(db.Float, nullable=True)     # Blood Pressure
    sg = db.Column(db.Float, nullable=True)     # Specific Gravity
    al = db.Column(db.Float, nullable=True)     # Albumin
    su = db.Column(db.Float, nullable=True)     # Sugar
    bgr = db.Column(db.Float, nullable=True)    # Blood Glucose Random
    bu = db.Column(db.Float, nullable=True)     # Blood Urea
    sc = db.Column(db.Float, nullable=True)     # Serum Creatinine
    sod = db.Column(db.Float, nullable=True)    # Sodium
    pot = db.Column(db.Float, nullable=True)    # Potassium
    hemo = db.Column(db.Float, nullable=True)   # Hemoglobin
    pcv = db.Column(db.Float, nullable=True)    # Packed Cell Volume
    wc = db.Column(db.Float, nullable=True)     # White Blood Cell Count
    rc = db.Column(db.Float, nullable=True)     # Red Blood Cell Count
    
    # Categorical features (stored as strings to match original values, e.g. normal/abnormal, yes/no)
    rbc = db.Column(db.String(20), nullable=True)   # Red Blood Cells
    pc = db.Column(db.String(20), nullable=True)    # Pus Cell
    pcc = db.Column(db.String(20), nullable=True)   # Pus Cell Clumps
    ba = db.Column(db.String(20), nullable=True)    # Bacteria
    htn = db.Column(db.String(20), nullable=True)   # Hypertension
    dm = db.Column(db.String(20), nullable=True)    # Diabetes Mellitus
    cad = db.Column(db.String(20), nullable=True)   # Coronary Artery Disease
    appet = db.Column(db.String(20), nullable=True) # Appetite
    pe = db.Column(db.String(20), nullable=True)    # Pedal Edema
    ane = db.Column(db.String(20), nullable=True)   # Anemia

    # Relationships
    predictions = db.relationship('Prediction', backref='clinical_record', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ClinicalRecord ID {self.id} for Patient {self.patient_id}>"

class Prediction(db.Model):
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    clinical_record_id = db.Column(db.Integer, db.ForeignKey('clinical_records.id', ondelete='CASCADE'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False)
    predicted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    prediction_outcome = db.Column(db.String(30), nullable=False) # CKD Positive / CKD Negative
    risk_probability = db.Column(db.Float, nullable=False)        # e.g. 0.9482
    threshold_used = db.Column(db.Float, nullable=False)          # e.g. 0.50
    
    # Explainable AI plot references (relative static paths)
    shap_waterfall_path = db.Column(db.String(256), nullable=True)
    lime_plot_path = db.Column(db.String(256), nullable=True)
    
    doctor_notes = db.Column(db.Text, nullable=True)
    report_id = db.Column(db.String(50), unique=True, nullable=True) # e.g. REP-2026-XXXX-XXXX
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Prediction ID {self.id} ({self.prediction_outcome})>"

class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(256), nullable=False)

    def __repr__(self):
        return f"<SystemSettings {self.key}={self.value}>"
