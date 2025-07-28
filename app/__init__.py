from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
from config import config
import os

# Import models to get db
from app.models import db

# Initialize other extensions
login_manager = LoginManager()
socketio = SocketIO()

def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    
    # Configure Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Import and register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    
    from app.configuration import bp as config_bp
    app.register_blueprint(config_bp, url_prefix='/config')
    
    # Main routes
    from app import routes
    app.register_blueprint(routes.bp)
    
    return app