import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://postgres:deno0707@localhost:5432/abzone'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Brevo Email settings
    BREVO_API_KEY = os.environ.get('BREVO_API_KEY')
    BREVO_SENDER_EMAIL = os.environ.get('BREVO_SENDER_EMAIL') or 'noreply@abzhardware.com'
    BREVO_SENDER_NAME = os.environ.get('BREVO_SENDER_NAME') or 'ABZ Hardware'
    
    # Application settings
    APP_NAME = 'ABZ Sales Portal'
    APP_URL = os.environ.get('APP_URL') or 'http://localhost:5000'
    
    # Password reset settings
    PASSWORD_RESET_EXPIRY_HOURS = 24
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 