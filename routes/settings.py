import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file, current_app, Response, abort
from flask_login import login_required, current_user
from database import db
from services.settings_service import SettingsService
from services.backup import BackupService
from routes.auth import roles_required

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@roles_required('Admin')
def index():
    # Fetch current setting values
    hospital_name = SettingsService.get_setting('hospital_name')
    doctor_name = SettingsService.get_setting('doctor_name')
    theme = SettingsService.get_setting('theme')
    threshold = SettingsService.get_setting('prediction_threshold')
    
    # Scan backups directory for list of database files
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    backup_dir = os.path.join(base_dir, 'database', 'backups')
    
    backup_files = []
    if os.path.exists(backup_dir):
        backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
        backup_files.sort(reverse=True) # Show newest backups first
        
    if request.method == 'POST' and 'update_settings' in request.form:
        new_hosp = request.form.get('hospital_name', '').strip()
        new_doc = request.form.get('doctor_name', '').strip()
        new_theme = request.form.get('theme', 'light').strip()
        new_thresh_str = request.form.get('prediction_threshold', '0.50').strip()
        
        if not new_hosp or not new_doc:
            flash("Hospital name and Doctor name cannot be empty.", "warning")
            return redirect(url_for('settings.index'))
            
        try:
            new_thresh = float(new_thresh_str)
            if new_thresh < 0.0 or new_thresh > 1.0:
                raise ValueError()
        except ValueError:
            flash("Prediction threshold must be a decimal between 0.0 and 1.0.", "danger")
            return redirect(url_for('settings.index'))
            
        SettingsService.set_setting('hospital_name', new_hosp)
        SettingsService.set_setting('doctor_name', new_doc)
        SettingsService.set_setting('theme', new_theme)
        SettingsService.set_setting('prediction_threshold', new_thresh)
        
        flash("System configurations updated successfully.", "success")
        return redirect(url_for('settings.index'))
        
    return render_template(
        'settings/index.html',
        hospital_name=hospital_name,
        doctor_name=doctor_name,
        theme=theme,
        prediction_threshold=threshold,
        backup_files=backup_files,
        app_version="1.0.0 (IEEE Release)",
        model_version="1.2.0 (Voting Classifier)"
    )

@settings_bp.route('/settings/backup', methods=['POST'])
@login_required
@roles_required('Admin')
def trigger_backup():
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    db_path = os.path.join(base_dir, 'database', 'nephroinsight.db')
    backup_dir = os.path.join(base_dir, 'database', 'backups')
    
    try:
        backup_path = BackupService.backup_database(db_path, backup_dir)
        filename = os.path.basename(backup_path)
        flash(f"Database backed up successfully as: {filename}", "success")
    except Exception as e:
        flash(f"Database backup failed: {e}", "danger")
        
    return redirect(url_for('settings.index'))

@settings_bp.route('/settings/restore/<string:filename>', methods=['POST'])
@login_required
@roles_required('Admin')
def restore_backup(filename):
    # Sanity check against directory traversal
    if '..' in filename or not filename.endswith('.db'):
        abort(400)
        
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    db_path = os.path.join(base_dir, 'database', 'nephroinsight.db')
    backup_file_path = os.path.join(base_dir, 'database', 'backups', filename)
    
    try:
        BackupService.restore_database(backup_file_path, db_path)
        flash(f"System database successfully restored from snapshot: {filename}", "success")
    except Exception as e:
        flash(f"System restore failed: {e}", "danger")
        
    return redirect(url_for('settings.index'))

@settings_bp.route('/settings/export', methods=['GET'])
@login_required
@roles_required('Admin')
def export_data():
    try:
        json_data = BackupService.export_data_to_json()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nephroinsight_export_{timestamp}.json"
        
        return Response(
            json_data,
            mimetype="application/json",
            headers={"Content-disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        flash(f"Export failed: {e}", "danger")
        return redirect(url_for('settings.index'))

@settings_bp.route('/settings/import', methods=['POST'])
@login_required
@roles_required('Admin')
def import_data():
    file = request.files.get('import_file')
    if not file or not file.filename.endswith('.json'):
        flash("Please upload a valid JSON backup file.", "warning")
        return redirect(url_for('settings.index'))
        
    try:
        content = file.read().decode('utf-8')
        imported_count = BackupService.import_data_from_json(content)
        flash(f"Successfully imported {imported_count} patient histories and medical prediction files.", "success")
    except Exception as e:
        flash(f"Import process failed: {e}", "danger")
        
    return redirect(url_for('settings.index'))
