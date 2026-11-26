import os
import shutil
import json
from datetime import datetime, date
from database import db
from services.db_model import User, Patient, ClinicalRecord, Prediction

class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle Date and DateTime objects.
    """
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

class BackupService:
    @staticmethod
    def backup_database(db_path, backup_dir):
        """
        Creates a copy of the active SQLite database.
        """
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"nephroinsight_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Verify db file exists
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Active database at {db_path} does not exist.")
            
        shutil.copy2(db_path, backup_path)
        return backup_path

    @staticmethod
    def restore_database(backup_file_path, db_path):
        """
        Restores active SQLite database from a backup file.
        """
        if not os.path.exists(backup_file_path):
            raise FileNotFoundError(f"Backup file at {backup_file_path} not found.")
            
        # Overwrite the active database file
        # Note: SQLAlchemy connection might hold a lock, but SQLite usually allows copy-over
        # Better yet, close all sessions first
        db.session.remove()
        db.engine.dispose()
        
        shutil.copy2(backup_file_path, db_path)

    @staticmethod
    def export_data_to_json():
        """
        Exports Patients, ClinicalRecords, and Predictions to a JSON structure.
        """
        patients_list = []
        records_list = []
        predictions_list = []
        
        # Query patients
        patients = Patient.query.all()
        for p in patients:
            patients_list.append({
                'id': p.id,
                'patient_id': p.patient_id,
                'name': p.name,
                'dob': p.dob,
                'gender': p.gender,
                'contact': p.contact,
                'email': p.email,
                'address': p.address,
                'created_at': p.created_at,
                'updated_at': p.updated_at
            })
            
        # Query records
        records = ClinicalRecord.query.all()
        for r in records:
            records_list.append({
                'id': r.id,
                'patient_id': r.patient_id,
                'created_at': r.created_at,
                'updated_at': r.updated_at,
                'age': r.age, 'bp': r.bp, 'sg': r.sg, 'al': r.al, 'su': r.su,
                'rbc': r.rbc, 'pc': r.pc, 'pcc': r.pcc, 'ba': r.ba,
                'bgr': r.bgr, 'bu': r.bu, 'sc': r.sc, 'sod': r.sod, 'pot': r.pot,
                'hemo': r.hemo, 'pcv': r.pcv, 'wc': r.wc, 'rc': r.rc,
                'htn': r.htn, 'dm': r.dm, 'cad': r.cad, 'appet': r.appet,
                'pe': r.pe, 'ane': r.ane
            })
            
        # Query predictions
        predictions = Prediction.query.all()
        for pr in predictions:
            predictions_list.append({
                'id': pr.id,
                'clinical_record_id': pr.clinical_record_id,
                'patient_id': pr.patient_id,
                'predicted_by_id': pr.predicted_by_id,
                'prediction_outcome': pr.prediction_outcome,
                'risk_probability': pr.risk_probability,
                'threshold_used': pr.threshold_used,
                'shap_waterfall_path': pr.shap_waterfall_path,
                'lime_plot_path': pr.lime_plot_path,
                'doctor_notes': pr.doctor_notes,
                'report_id': pr.report_id,
                'created_at': pr.created_at
            })
            
        data = {
            'metadata': {
                'exported_at': datetime.now().isoformat(),
                'version': '1.0.0',
                'app': 'NephroInsight AI'
            },
            'patients': patients_list,
            'clinical_records': records_list,
            'predictions': predictions_list
        }
        
        return json.dumps(data, cls=DateTimeEncoder, indent=2)

    @staticmethod
    def import_data_from_json(json_content):
        """
        Imports Patients, ClinicalRecords, and Predictions from JSON content.
        Resolves foreign keys using patient_id mapping to prevent conflicts.
        """
        data = json.loads(json_content)
        
        # Verify schema
        if 'patients' not in data or 'clinical_records' not in data or 'predictions' not in data:
            raise ValueError("Invalid export format. Missing core fields.")
            
        # Keep track of old patient ID -> new patient DB model
        patient_map = {}
        
        # 1. Import Patients
        for p_data in data['patients']:
            # Check if patient already exists by patient_id
            existing = Patient.query.filter_by(patient_id=p_data['patient_id']).first()
            if existing:
                # Use existing patient, update metadata
                existing.name = p_data['name']
                existing.dob = datetime.fromisoformat(p_data['dob']).date()
                existing.gender = p_data['gender']
                existing.contact = p_data['contact']
                existing.email = p_data.get('email')
                existing.address = p_data.get('address')
                patient_map[p_data['id']] = existing
            else:
                # Create new patient
                new_p = Patient(
                    patient_id=p_data['patient_id'],
                    name=p_data['name'],
                    dob=datetime.fromisoformat(p_data['dob']).date(),
                    gender=p_data['gender'],
                    contact=p_data['contact'],
                    email=p_data.get('email'),
                    address=p_data.get('address'),
                    created_at=datetime.fromisoformat(p_data['created_at']) if 'created_at' in p_data else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(p_data['updated_at']) if 'updated_at' in p_data else datetime.utcnow()
                )
                db.session.add(new_p)
                db.session.flush() # Populate ID
                patient_map[p_data['id']] = new_p
                
        # 2. Import Clinical Records
        # Keep map of old record ID -> new record DB model
        record_map = {}
        for r_data in data['clinical_records']:
            # Find patient model
            old_p_id = r_data['patient_id']
            p_model = patient_map.get(old_p_id)
            if not p_model:
                # Skip if patient mapping failed
                continue
                
            # Create new record
            new_r = ClinicalRecord(
                patient=p_model,
                created_at=datetime.fromisoformat(r_data['created_at']) if 'created_at' in r_data else datetime.utcnow(),
                updated_at=datetime.fromisoformat(r_data['updated_at']) if 'updated_at' in r_data else datetime.utcnow(),
                age=r_data.get('age'), bp=r_data.get('bp'), sg=r_data.get('sg'),
                al=r_data.get('al'), su=r_data.get('su'), rbc=r_data.get('rbc'),
                pc=r_data.get('pc'), pcc=r_data.get('pcc'), ba=r_data.get('ba'),
                bgr=r_data.get('bgr'), bu=r_data.get('bu'), sc=r_data.get('sc'),
                sod=r_data.get('sod'), pot=r_data.get('pot'), hemo=r_data.get('hemo'),
                pcv=r_data.get('pcv'), wc=r_data.get('wc'), rc=r_data.get('rc'),
                htn=r_data.get('htn'), dm=r_data.get('dm'), cad=r_data.get('cad'),
                appet=r_data.get('appet'), pe=r_data.get('pe'), ane=r_data.get('ane')
            )
            db.session.add(new_r)
            db.session.flush()
            record_map[r_data['id']] = new_r
            
        # 3. Import Predictions
        for pr_data in data['predictions']:
            old_p_id = pr_data['patient_id']
            old_r_id = pr_data['clinical_record_id']
            
            p_model = patient_map.get(old_p_id)
            r_model = record_map.get(old_r_id)
            
            if not p_model or not r_model:
                continue
                
            # Check if prediction report_id already exists to prevent duplicate prediction imports
            if pr_data.get('report_id'):
                existing_pred = Prediction.query.filter_by(report_id=pr_data['report_id']).first()
                if existing_pred:
                    continue
                    
            new_pred = Prediction(
                patient=p_model,
                clinical_record=r_model,
                predicted_by_id=None, # Clear user bindings to prevent import login crashes
                prediction_outcome=pr_data['prediction_outcome'],
                risk_probability=pr_data['risk_probability'],
                threshold_used=pr_data['threshold_used'],
                shap_waterfall_path=pr_data.get('shap_waterfall_path'),
                lime_plot_path=pr_data.get('lime_plot_path'),
                doctor_notes=pr_data.get('doctor_notes'),
                report_id=pr_data.get('report_id'),
                created_at=datetime.fromisoformat(pr_data['created_at']) if 'created_at' in pr_data else datetime.utcnow()
            )
            db.session.add(new_pred)
            
        db.session.commit()
        return len(patient_map)
