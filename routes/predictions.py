import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_from_directory, current_app
from flask_login import login_required, current_user
from datetime import datetime
from database import db
from services.db_model import Patient, ClinicalRecord, Prediction
from services.inference import InferenceService
from services.xai import XAIService
from services.report_pdf import ReportPDFService
from services.settings_service import SettingsService
from utils.validators import CLINICAL_METADATA, validate_clinical_inputs
from utils.recommendations import generate_clinical_recommendations
from routes.auth import roles_required

predictions_bp = Blueprint('predictions', __name__)

@predictions_bp.route('/predict/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@roles_required('Admin', 'Doctor')
def predict(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    # Pre-populate using the most recent clinical record if it exists
    latest_record = ClinicalRecord.query.filter_by(patient_id=patient_id).order_by(ClinicalRecord.created_at.desc()).first()
    
    # Calculate age from patient DOB for the default age input
    calculated_age = datetime.now().year - patient.dob.year
    
    if request.method == 'POST':
        # Collect raw form inputs
        form_data = {}
        for field in CLINICAL_METADATA.keys():
            form_data[field] = request.form.get(field, '').strip()
            
        # Validate inputs
        validated_data, errors = validate_clinical_inputs(form_data)
        
        if errors:
            for err in errors:
                flash(err, "warning")
            return render_template(
                'predictions/form.html',
                patient=patient,
                metadata=CLINICAL_METADATA,
                latest_record=latest_record or form_data,
                calculated_age=calculated_age
            )
            
        # 1. Save new Clinical Record
        new_record = ClinicalRecord(
            patient_id=patient.id,
            **validated_data
        )
        db.session.add(new_record)
        db.session.commit()
        
        # 2. Perform Inference
        inference_service = InferenceService()
        threshold = SettingsService.get_setting('prediction_threshold')
        
        # We need raw format for the prediction and XAI pipelines (handling default imputation internally)
        results = inference_service.predict(validated_data, threshold=threshold)
        
        # 3. Save initial Prediction block to generate Prediction ID
        new_pred = Prediction(
            clinical_record_id=new_record.id,
            patient_id=patient.id,
            predicted_by_id=current_user.id,
            prediction_outcome=results['outcome'],
            risk_probability=results['ckd_risk_probability'],
            threshold_used=threshold,
            doctor_notes="",
            report_id=""
        )
        db.session.add(new_pred)
        db.session.commit()
        
        # Generate unique report ID
        report_id = f"REP-{datetime.now().strftime('%Y%m%d')}-{new_pred.id:04d}"
        new_pred.report_id = report_id
        
        # 4. Generate local explainable AI plots (SHAP & LIME)
        xai_service = XAIService()
        xai_results = xai_service.generate_local_explanations(
            prediction_id=new_pred.id,
            raw_input=validated_data,
            scaled_features=results['scaled_features'],
            encoded_df=results['encoded_df']
        )
        
        # Update prediction record with visual plot paths and default doctor interpretations
        new_pred.shap_waterfall_path = xai_results['shap_waterfall']
        new_pred.lime_plot_path = xai_results['lime_plot']
        new_pred.doctor_notes = xai_results['doctor_explanation']
        db.session.commit()
        
        # 5. Generate clinical recommendations
        recs = generate_clinical_recommendations(
            new_pred.prediction_outcome,
            new_pred.risk_probability,
            validated_data
        )
        recs['patient_explanation'] = xai_results['patient_explanation']
        
        # 6. Generate professional PDF report
        hospital_name = SettingsService.get_setting('hospital_name')
        doctor_name = SettingsService.get_setting('doctor_name')
        
        try:
            ReportPDFService.generate_report(
                prediction=new_pred,
                patient=patient,
                record=new_record,
                recommendations=recs,
                hospital_name=hospital_name,
                doctor_name=doctor_name
            )
        except Exception as e:
            print(f"Error compiling PDF report for prediction {new_pred.id}: {e}")
            flash("Clinical prediction succeeded, but PDF report generation failed.", "warning")
            
        flash("Clinical decision support prediction completed successfully.", "success")
        return redirect(url_for('predictions.prediction_result', id=new_pred.id))
        
    return render_template(
        'predictions/form.html',
        patient=patient,
        metadata=CLINICAL_METADATA,
        latest_record=latest_record,
        calculated_age=calculated_age
    )

@predictions_bp.route('/predictions/result/<int:id>')
@login_required
def prediction_result(id):
    prediction = Prediction.query.get_or_404(id)
    patient = prediction.patient
    record = prediction.clinical_record
    
    # Construct validated dict for recommendation engine
    record_dict = {}
    for col in CLINICAL_METADATA.keys():
        record_dict[col] = getattr(record, col, None)
        
    # Re-run XAI/Recommendation engine to fetch structures
    # (Explanations were cached in DB, but recommendations can be computed on the fly)
    xai_service = XAIService()
    
    # We reconstruct patient explanation to show
    # Since we need patient explanation in UI, let's recalculate or pull it from cached logs
    # In xai_service, we save LIME list to compute explanations. Let's recalculate LIME list on-the-fly
    # or recreate recommendations
    # To keep it extremely clean, let's recalculate the patient-friendly description
    results = InferenceService().predict(record_dict, threshold=prediction.threshold_used)
    
    # LIME explanations are recalculated to show contributor list in frontend
    # This keeps results interactive and displays them in tables!
    # LIME takes under 0.5s to generate list
    try:
        exp = xai_service.lime_explainer.explain_instance(
            data_row=results['scaled_features'][0],
            predict_fn=InferenceService().model.predict_proba,
            num_features=10
        )
        lime_list = exp.as_list()
    except Exception as e:
        print(f"Error recreating LIME list for UI: {e}")
        lime_list = []
        
    recs = generate_clinical_recommendations(
        prediction.prediction_outcome,
        prediction.risk_probability,
        record_dict
    )
    
    patient_explanation = xai_service._generate_patient_text(lime_list, record_dict)
    
    return render_template(
        'predictions/result.html',
        prediction=prediction,
        patient=patient,
        record=record,
        recommendations=recs,
        patient_explanation=patient_explanation,
        lime_list=lime_list,
        metadata=CLINICAL_METADATA
    )

@predictions_bp.route('/predictions/result/<int:id>/update_notes', methods=['POST'])
@login_required
@roles_required('Admin', 'Doctor')
def update_notes(id):
    prediction = Prediction.query.get_or_404(id)
    notes = request.form.get('doctor_notes', '').strip()
    
    prediction.doctor_notes = notes
    db.session.commit()
    
    # Re-generate the PDF report with the updated notes
    patient = prediction.patient
    record = prediction.clinical_record
    
    record_dict = {}
    for col in CLINICAL_METADATA.keys():
        record_dict[col] = getattr(record, col, None)
        
    xai_service = XAIService()
    results = InferenceService().predict(record_dict, threshold=prediction.threshold_used)
    
    try:
        exp = xai_service.lime_explainer.explain_instance(
            data_row=results['scaled_features'][0],
            predict_fn=InferenceService().model.predict_proba,
            num_features=10
        )
        lime_list = exp.as_list()
    except:
        lime_list = []
        
    recs = generate_clinical_recommendations(
        prediction.prediction_outcome,
        prediction.risk_probability,
        record_dict
    )
    recs['patient_explanation'] = xai_service._generate_patient_text(lime_list, record_dict)
    
    hospital_name = SettingsService.get_setting('hospital_name')
    doctor_name = SettingsService.get_setting('doctor_name')
    
    try:
        ReportPDFService.generate_report(
            prediction=prediction,
            patient=patient,
            record=record,
            recommendations=recs,
            hospital_name=hospital_name,
            doctor_name=doctor_name
        )
        flash("Doctor notes updated and clinical PDF report re-compiled successfully.", "success")
    except Exception as e:
        print(f"Error updating report PDF: {e}")
        flash("Notes saved, but PDF update failed.", "warning")
        
    return redirect(url_for('predictions.prediction_result', id=id))

@predictions_bp.route('/predictions/report/<string:report_id>')
@login_required
def download_report(report_id):
    # Find PDF file
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    reports_dir = os.path.join(base_dir, 'reports')
    filename = f"Report_{report_id}.pdf"
    
    if not os.path.exists(os.path.join(reports_dir, filename)):
        # Try to regenerate the report if file is missing but prediction exists
        prediction = Prediction.query.filter_by(report_id=report_id).first()
        if prediction:
            patient = prediction.patient
            record = prediction.clinical_record
            record_dict = {col: getattr(record, col) for col in CLINICAL_METADATA.keys()}
            
            xai_service = XAIService()
            results = InferenceService().predict(record_dict, threshold=prediction.threshold_used)
            try:
                exp = xai_service.lime_explainer.explain_instance(
                    data_row=results['scaled_features'][0],
                    predict_fn=InferenceService().model.predict_proba,
                    num_features=10
                )
                lime_list = exp.as_list()
            except:
                lime_list = []
                
            recs = generate_clinical_recommendations(
                prediction.prediction_outcome,
                prediction.risk_probability,
                record_dict
            )
            recs['patient_explanation'] = xai_service._generate_patient_text(lime_list, record_dict)
            
            hospital_name = SettingsService.get_setting('hospital_name')
            doctor_name = SettingsService.get_setting('doctor_name')
            
            try:
                ReportPDFService.generate_report(
                    prediction=prediction,
                    patient=patient,
                    record=record,
                    recommendations=recs,
                    hospital_name=hospital_name,
                    doctor_name=doctor_name
                )
                return send_from_directory(reports_dir, filename)
            except Exception as e:
                print(f"Error regenerating missing report: {e}")
                
        abort(404)
        
    return send_from_directory(reports_dir, filename)
