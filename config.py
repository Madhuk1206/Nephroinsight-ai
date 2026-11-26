import os

class Config:
    # Base directories
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'nephroinsight-ai-clinical-secret-key-92837482')
    
    # SQLAlchemy configuration
    DATABASE_DIR = os.path.join(BASE_DIR, 'database')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(DATABASE_DIR, 'nephroinsight.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Application directories
    MODELS_DIR = os.path.join(BASE_DIR, 'models')
    ML_MODELS_DIR = os.path.join(BASE_DIR, 'ml_models') # Fallback/Alternative mapping
    REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
    STATIC_DIR = os.path.join(BASE_DIR, 'static')
    XAI_PLOTS_DIR = os.path.join(STATIC_DIR, 'xai_plots')
    
    # Settings default values
    DEFAULT_HOSPITAL_NAME = "NephroInsight Medical Center"
    DEFAULT_DOCTOR_NAME = "Dr. Jane Smith, MD"
    DEFAULT_PREDICTION_THRESHOLD = 0.50
    DEFAULT_THEME = "light"
    
    @classmethod
    def init_app(cls, app):
        # Create necessary directories if they do not exist
        os.makedirs(cls.DATABASE_DIR, exist_ok=True)
        os.makedirs(cls.REPORTS_DIR, exist_ok=True)
        os.makedirs(cls.XAI_PLOTS_DIR, exist_ok=True)
        
        # Log directory creation
        print(f"Database Directory: {cls.DATABASE_DIR}")
        print(f"Reports Directory: {cls.REPORTS_DIR}")
        print(f"XAI Plots Directory: {cls.XAI_PLOTS_DIR}")
