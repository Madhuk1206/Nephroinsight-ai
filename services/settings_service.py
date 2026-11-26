from database import db
from services.db_model import SystemSettings
from config import Config

class SettingsService:
    @staticmethod
    def get_setting(key, default=None):
        """
        Retrieves a system setting from the database, falling back to Config defaults.
        """
        try:
            setting = SystemSettings.query.filter_by(key=key).first()
            if setting:
                val = setting.value
                if key == 'prediction_threshold':
                    return float(val)
                return val
        except Exception as e:
            print(f"Error fetching setting {key}: {e}")
            
        # Config fallbacks
        if key == 'hospital_name':
            return Config.DEFAULT_HOSPITAL_NAME
        elif key == 'doctor_name':
            return Config.DEFAULT_DOCTOR_NAME
        elif key == 'prediction_threshold':
            return Config.DEFAULT_PREDICTION_THRESHOLD
        elif key == 'theme':
            return Config.DEFAULT_THEME
        return default

    @staticmethod
    def set_setting(key, value):
        """
        Saves or updates a system setting in the database.
        """
        setting = SystemSettings.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
        else:
            setting = SystemSettings(key=key, value=str(value))
            db.session.add(setting)
        db.session.commit()
        return value
