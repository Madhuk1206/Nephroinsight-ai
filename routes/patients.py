from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from datetime import datetime
from database import db
from services.db_model import Patient, ClinicalRecord, Prediction
from routes.auth import roles_required

patients_bp = Blueprint('patients', __name__)

def generate_patient_id():
    """
    Generates a patient ID like NI-2026-0001 based on current year and patient count.
    """
    current_year = datetime.now().year
    # Count how many patients registered this year
    # SQLite friendly query for year extraction
    start_date = datetime(current_year, 1, 1)
    end_date = datetime(current_year, 12, 31, 23, 59, 59)
    count = Patient.query.filter(Patient.created_at.between(start_date, end_date)).count()
    return f"NI-{current_year}-{(count + 1):04d}"

@patients_bp.route('/patients')
@login_required
def list_patients():
    search = request.args.get('search', '').strip()
    gender = request.args.get('gender', '').strip()
    sort_by = request.args.get('sort_by', 'created_at').strip()
    order = request.args.get('order', 'desc').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    query = Patient.query
    
    # Filtering
    if search:
        query = query.filter(
            (Patient.name.like(f"%{search}%")) |
            (Patient.patient_id.like(f"%{search}%")) |
            (Patient.contact.like(f"%{search}%"))
        )
    if gender:
        query = query.filter(Patient.gender == gender)
        
    # Sorting
    if order == 'asc':
        if sort_by == 'name':
            query = query.order_by(Patient.name.asc())
        elif sort_by == 'patient_id':
            query = query.order_by(Patient.patient_id.asc())
        else:
            query = query.order_by(Patient.created_at.asc())
    else:
        if sort_by == 'name':
            query = query.order_by(Patient.name.desc())
        elif sort_by == 'patient_id':
            query = query.order_by(Patient.patient_id.desc())
        else:
            query = query.order_by(Patient.created_at.desc())
            
    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    patients = pagination.items
    
    return render_template(
        'patients/list.html',
        patients=patients,
        pagination=pagination,
        search=search,
        gender=gender,
        sort_by=sort_by,
        order=order
    )

@patients_bp.route('/patients/register', methods=['GET', 'POST'])
@login_required
@roles_required('Admin', 'Doctor', 'Receptionist')
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        dob_str = request.form.get('dob', '').strip()
        gender = request.form.get('gender', '').strip()
        contact = request.form.get('contact', '').strip()
        email = request.form.get('email', '').strip() or None
        address = request.form.get('address', '').strip() or None
        
        if not name or not dob_str or not gender or not contact:
            flash("Please complete all required fields.", "warning")
            return redirect(url_for('patients.register'))
            
        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date of birth format.", "danger")
            return redirect(url_for('patients.register'))
            
        patient_id = generate_patient_id()
        
        patient = Patient(
            patient_id=patient_id,
            name=name,
            dob=dob,
            gender=gender,
            contact=contact,
            email=email,
            address=address
        )
        
        db.session.add(patient)
        db.session.commit()
        
        flash(f"Patient {name} has been successfully registered with ID {patient_id}.", "success")
        return redirect(url_for('patients.view_patient', id=patient.id))
        
    return render_template('patients/register.html')

@patients_bp.route('/patients/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@roles_required('Admin', 'Doctor', 'Receptionist')
def edit_patient(id):
    patient = Patient.query.get_or_404(id)
    
    if request.method == 'POST':
        patient.name = request.form.get('name', '').strip()
        dob_str = request.form.get('dob', '').strip()
        patient.gender = request.form.get('gender', '').strip()
        patient.contact = request.form.get('contact', '').strip()
        patient.email = request.form.get('email', '').strip() or None
        patient.address = request.form.get('address', '').strip() or None
        
        if not patient.name or not dob_str or not patient.gender or not patient.contact:
            flash("Please complete all required fields.", "warning")
            return redirect(url_for('patients.edit_patient', id=id))
            
        try:
            patient.dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date of birth format.", "danger")
            return redirect(url_for('patients.edit_patient', id=id))
            
        db.session.commit()
        flash("Patient details updated successfully.", "success")
        return redirect(url_for('patients.view_patient', id=id))
        
    return render_template('patients/edit.html', patient=patient)

@patients_bp.route('/patients/delete/<int:id>', methods=['POST'])
@login_required
@roles_required('Admin', 'Doctor')
def delete_patient(id):
    patient = Patient.query.get_or_404(id)
    name = patient.name
    
    # Delete local prediction images associated with the patient from disk
    predictions = Prediction.query.filter_by(patient_id=id).all()
    base_static = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
    for pred in predictions:
        if pred.shap_waterfall_path:
            full_path = os.path.join(base_static, pred.shap_waterfall_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    print(f"Error removing shap plot: {e}")
        if pred.lime_plot_path:
            full_path = os.path.join(base_static, pred.lime_plot_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    print(f"Error removing lime plot: {e}")
                    
    db.session.delete(patient)
    db.session.commit()
    flash(f"Patient {name} and all associated records have been deleted.", "success")
    return redirect(url_for('patients.list_patients'))

@patients_bp.route('/patients/view/<int:id>')
@login_required
def view_patient(id):
    patient = Patient.query.get_or_404(id)
    
    # Get visit history
    # We query predictions linked to the patient
    predictions_history = Prediction.query.filter_by(patient_id=id).order_by(Prediction.created_at.desc()).all()
    
    return render_template(
        'patients/view.html',
        patient=patient,
        predictions=predictions_history
    )
