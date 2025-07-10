from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def init_app(app):
    """Initialize Flask extensions"""
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    # Set up user loader
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Initialize email service
    from email_service import init_email_service
    init_email_service(app.config.get('BREVO_API_KEY')) 