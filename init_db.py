#!/usr/bin/env python3
"""
Database initialization script for NextCare
Creates tables and inserts default data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from werkzeug.security import generate_password_hash

def init_database():
    """Initialize database with tables and default data"""
    app = create_app()
    
    with app.app_context():
        # Import here to avoid circular imports
        from app.models import db, User, Machine, Parameter
        
        # Create all tables
        db.create_all()
        
        # Create default admin user
        admin_user = User(
            username='admin',
            email='admin@nextcare.com',
            role='admin'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        
        # Create sample machines
        machine1 = Machine(
            name='Production Line A',
            description='Main production line for assembly',
            location='Factory Floor 1'
        )
        
        machine2 = Machine(
            name='Packaging Unit B',
            description='Automated packaging system',
            location='Factory Floor 2'
        )
        
        db.session.add(machine1)
        db.session.add(machine2)
        db.session.commit()
        
        # Create sample parameters for machine 1
        parameters = [
            Parameter(machine_id=machine1.machine_id, name='Temperature', register_address='D20', unit='°C', min_value=20.0, max_value=80.0),
            Parameter(machine_id=machine1.machine_id, name='Vibration', register_address='D21', unit='Hz', min_value=0.0, max_value=100.0),
            Parameter(machine_id=machine1.machine_id, name='Shock', register_address='D22', unit='g', min_value=0.0, max_value=10.0),
            Parameter(machine_id=machine1.machine_id, name='Oil Supply', register_address='D23', unit='%', min_value=0.0, max_value=100.0),
            Parameter(machine_id=machine1.machine_id, name='Sound', register_address='D24', unit='dB', min_value=30.0, max_value=90.0),
        ]
        
        for param in parameters:
            db.session.add(param)
        
        # Create sample parameters for machine 2
        parameters2 = [
            Parameter(machine_id=machine2.machine_id, name='Temperature', register_address='D25', unit='°C', min_value=18.0, max_value=75.0),
            Parameter(machine_id=machine2.machine_id, name='Pressure', register_address='D26', unit='PSI', min_value=0.0, max_value=150.0),
            Parameter(machine_id=machine2.machine_id, name='Speed', register_address='D27', unit='RPM', min_value=0.0, max_value=3000.0),
        ]
        
        for param in parameters2:
            db.session.add(param)
        
        db.session.commit()
        
        print("Database initialized successfully!")
        print("Default admin user created:")
        print("  Username: admin")
        print("  Password: admin123")
        print(f"Created {len(parameters) + len(parameters2)} parameters across 2 machines")

if __name__ == '__main__':
    init_database()