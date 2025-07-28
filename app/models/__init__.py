from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    machine_assignments = db.relationship('UserMachineAssignment', backref='user', cascade='all, delete-orphan')
    acknowledged_alerts = db.relationship('Alert', foreign_keys='Alert.acknowledged_by', backref='acknowledger')
    
    def get_id(self):
        return str(self.user_id)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role):
        return self.role == role
    
    def can_access_machine(self, machine_id):
        if self.role in ['admin', 'manager']:
            return True
        return any(assignment.machine_id == machine_id for assignment in self.machine_assignments)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Machine(db.Model):
    __tablename__ = 'machines'
    
    machine_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parameters = db.relationship('Parameter', backref='machine', cascade='all, delete-orphan')
    user_assignments = db.relationship('UserMachineAssignment', backref='machine', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'machine_id': self.machine_id,
            'name': self.name,
            'description': self.description,
            'location': self.location,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'parameter_count': len(self.parameters)
        }

class Parameter(db.Model):
    __tablename__ = 'parameters'
    
    parameter_id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machines.machine_id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    register_address = db.Column(db.String(10), nullable=False)
    unit = db.Column(db.String(10), nullable=False)
    min_value = db.Column(db.Numeric(10, 2))
    max_value = db.Column(db.Numeric(10, 2))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sensor_data = db.relationship('SensorData', backref='parameter', cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='parameter', cascade='all, delete-orphan')
    
    def get_latest_value(self):
        latest_data = SensorData.query.filter_by(parameter_id=self.parameter_id)\
                                    .order_by(SensorData.timestamp.desc()).first()
        return latest_data.value if latest_data else None
    
    def get_register_number(self):
        # Extract number from D20, D21, etc.
        return int(self.register_address[1:]) if self.register_address.startswith('D') else None
    
    def to_dict(self):
        return {
            'parameter_id': self.parameter_id,
            'machine_id': self.machine_id,
            'name': self.name,
            'register_address': self.register_address,
            'unit': self.unit,
            'min_value': float(self.min_value) if self.min_value else None,
            'max_value': float(self.max_value) if self.max_value else None,
            'is_active': self.is_active,
            'latest_value': self.get_latest_value()
        }

class SensorData(db.Model):
    __tablename__ = 'sensor_data'
    
    data_id = db.Column(db.Integer, primary_key=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey('parameters.parameter_id'), nullable=False)
    value = db.Column(db.Numeric(10, 2), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    quality_code = db.Column(db.Integer, default=0)  # 0: good, 1: uncertain, 2: bad
    
    def to_dict(self):
        return {
            'data_id': self.data_id,
            'parameter_id': self.parameter_id,
            'value': float(self.value),
            'timestamp': self.timestamp.isoformat(),
            'quality_code': self.quality_code
        }

class UserMachineAssignment(db.Model):
    __tablename__ = 'user_machine_assignments'
    
    assignment_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('machines.machine_id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'machine_id'),)

class Alert(db.Model):
    __tablename__ = 'alerts'
    
    alert_id = db.Column(db.Integer, primary_key=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey('parameters.parameter_id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    threshold_value = db.Column(db.Numeric(10, 2))
    actual_value = db.Column(db.Numeric(10, 2))
    is_acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    acknowledged_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'alert_id': self.alert_id,
            'parameter_id': self.parameter_id,
            'message': self.message,
            'severity': self.severity,
            'threshold_value': float(self.threshold_value) if self.threshold_value else None,
            'actual_value': float(self.actual_value) if self.actual_value else None,
            'is_acknowledged': self.is_acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }