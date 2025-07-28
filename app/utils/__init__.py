"""
Utility functions for NextCare Industrial Monitoring System
"""

from functools import wraps
from flask import jsonify, request
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            if request.is_json:
                return jsonify({'error': 'Admin access required'}), 403
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def manager_or_admin_required(f):
    """Decorator to require manager or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'manager']:
            if request.is_json:
                return jsonify({'error': 'Manager or admin access required'}), 403
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def format_timestamp(timestamp):
    """Format timestamp for display"""
    if not timestamp:
        return 'N/A'
    return timestamp.strftime('%Y-%m-%d %H:%M:%S')

def format_value(value, unit=''):
    """Format numeric value for display"""
    if value is None:
        return 'N/A'
    
    try:
        float_val = float(value)
        if unit == '%':
            return f"{float_val:.1f}%"
        elif unit in ['°C', '°F']:
            return f"{float_val:.1f}{unit}"
        else:
            return f"{float_val:.2f} {unit}".strip()
    except (ValueError, TypeError):
        return str(value)

def get_alert_color(severity):
    """Get CSS color class for alert severity"""
    colors = {
        'low': 'info',
        'medium': 'warning', 
        'high': 'danger',
        'critical': 'dark'
    }
    return colors.get(severity, 'secondary')

def validate_register_address(address):
    """Validate register address format (D20, D21, etc.)"""
    if not address:
        return False
    
    if not address.startswith('D'):
        return False
    
    try:
        register_num = int(address[1:])
        return 20 <= register_num <= 99  # Valid range for our simulation
    except ValueError:
        return False

def safe_float(value, default=None):
    """Safely convert value to float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def truncate_text(text, max_length=50):
    """Truncate text to specified length"""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length-3] + '...'

class ParameterValidator:
    """Validator for parameter configuration"""
    
    @staticmethod
    def validate_parameter_data(data):
        """Validate parameter configuration data"""
        errors = []
        
        # Required fields
        required_fields = ['name', 'register_address', 'unit']
        for field in required_fields:
            if not data.get(field):
                errors.append(f"{field.replace('_', ' ').title()} is required")
        
        # Validate register address
        if data.get('register_address') and not validate_register_address(data['register_address']):
            errors.append("Register address must be in format D20-D99")
        
        # Validate numeric ranges
        min_val = safe_float(data.get('min_value'))
        max_val = safe_float(data.get('max_value'))
        
        if min_val is not None and max_val is not None and min_val >= max_val:
            errors.append("Minimum value must be less than maximum value")
        
        return errors

class DataQualityChecker:
    """Check data quality and generate warnings"""
    
    @staticmethod
    def check_value_quality(value, parameter):
        """Check if a sensor value is within expected range"""
        if value is None:
            return 'bad', 'No data received'
        
        try:
            float_val = float(value)
            
            # Check if within min/max bounds
            if parameter.min_value is not None and float_val < float(parameter.min_value):
                return 'bad', f'Value below minimum ({parameter.min_value})'
            
            if parameter.max_value is not None and float_val > float(parameter.max_value):
                return 'bad', f'Value exceeds maximum ({parameter.max_value})'
            
            # Check for realistic ranges based on parameter type
            warnings = DataQualityChecker._check_realistic_ranges(float_val, parameter.register_address)
            if warnings:
                return 'uncertain', warnings
            
            return 'good', 'Value within normal range'
            
        except (ValueError, TypeError):
            return 'bad', 'Invalid numeric value'
    
    @staticmethod
    def _check_realistic_ranges(value, register_address):
        """Check if value is within realistic ranges for parameter type"""
        realistic_ranges = {
            'D20': (0, 100),    # Temperature °C
            'D21': (0, 200),    # Vibration Hz
            'D22': (0, 20),     # Shock g
            'D23': (0, 100),    # Oil Supply %
            'D24': (0, 120),    # Sound dB
        }
        
        if register_address in realistic_ranges:
            min_realistic, max_realistic = realistic_ranges[register_address]
            if value < min_realistic or value > max_realistic:
                return f'Value outside realistic range ({min_realistic}-{max_realistic})'
        
        return None

# Template filters
def init_template_filters(app):
    """Initialize custom template filters"""
    
    @app.template_filter('timestamp')
    def timestamp_filter(timestamp):
        return format_timestamp(timestamp)
    
    @app.template_filter('value')
    def value_filter(value, unit=''):
        return format_value(value, unit)
    
    @app.template_filter('alert_color')
    def alert_color_filter(severity):
        return get_alert_color(severity)
    
    @app.template_filter('truncate')
    def truncate_filter(text, length=50):
        return truncate_text(text, length)