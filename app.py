import os
from flask import Flask, render_template
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from database import db
from config import Config

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    Config.init_app(app)
    
    # Initialize database
    db.init_app(app)
    
    # Setup login manager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)
    
    from services.db_model import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    # Register Blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.patients import patients_bp
    from routes.predictions import predictions_bp
    from routes.settings import settings_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(settings_bp)
    
    # Register Jinja global functions
    app.jinja_env.globals.update(round=round)
    
    # Inject global settings to all templates
    @app.context_processor
    def inject_settings():
        from services.settings_service import SettingsService
        # Default settings if database isn't fully ready
        theme = 'light'
        hospital_name = Config.DEFAULT_HOSPITAL_NAME
        doctor_name = Config.DEFAULT_DOCTOR_NAME
        
        try:
            theme = SettingsService.get_setting('theme')
            hospital_name = SettingsService.get_setting('hospital_name')
            doctor_name = SettingsService.get_setting('doctor_name')
        except Exception as e:
            print("Context settings lookup skipped:", e)
            
        return dict(
            system_theme=theme,
            system_hospital_name=hospital_name,
            system_doctor_name=doctor_name
        )
        
    # Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
        
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
        
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
        
    # Database and seed initialization
    with app.app_context():
        db.create_all()
        seed_default_users()
        
    return app

def seed_default_users():
    """
    Seeds default admin, doctor, and receptionist accounts if they do not exist.
    """
    from services.db_model import User
    
    users_to_seed = [
        {
            'username': 'admin',
            'name': 'System Administrator',
            'password': 'admin123',
            'role': 'Admin',
            'email': 'admin@nephroinsight.org'
        },
        {
            'username': 'doctor',
            'name': 'Dr. Jane Smith, MD',
            'password': 'doctor123',
            'role': 'Doctor',
            'email': 'j.smith@nephroinsight.org'
        },
        {
            'username': 'receptionist',
            'name': 'Sarah Jenkins',
            'password': 'receptionist123',
            'role': 'Receptionist',
            'email': 's.jenkins@nephroinsight.org'
        }
    ]
    
    for u_data in users_to_seed:
        existing = User.query.filter_by(username=u_data['username']).first()
        if not existing:
            user = User(
                username=u_data['username'],
                name=u_data['name'],
                password_hash=generate_password_hash(u_data['password'], method='pbkdf2:sha256'),
                role=u_data['role'],
                email=u_data['email']
            )
            db.session.add(user)
            print(f"Seeded user: {u_data['username']} ({u_data['role']})")
            
    db.session.commit()

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)
