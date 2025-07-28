import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///nextcare.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Mock PLC Configuration
    PLC_HOST = os.environ.get('PLC_HOST') or '127.0.0.1'
    PLC_PORT = int(os.environ.get('PLC_PORT') or 5020)
    
    # Data Collection Configuration
    DATA_COLLECTION_INTERVAL = int(os.environ.get('DATA_COLLECTION_INTERVAL') or 5)  # seconds
    
    # Register Mapping
    REGISTER_MAPPING = {
        'D20': {'name': 'Temperature', 'unit': '°C', 'min_val': 20, 'max_val': 80},
        'D21': {'name': 'Vibration', 'unit': 'Hz', 'min_val': 0, 'max_val': 100},
        'D22': {'name': 'Shock', 'unit': 'g', 'min_val': 0, 'max_val': 10},
        'D23': {'name': 'Oil Supply', 'unit': '%', 'min_val': 0, 'max_val': 100},
        'D24': {'name': 'Sound', 'unit': 'dB', 'min_val': 30, 'max_val': 90}
    }

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}