-- NextCare Industrial Monitoring System Database Schema

-- Drop tables if they exist (for development)
DROP TABLE IF EXISTS user_machine_assignments CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS sensor_data CASCADE;
DROP TABLE IF EXISTS parameters CASCADE;
DROP TABLE IF EXISTS machines CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Users table for authentication and role management
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'manager', 'engineer')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Machines table for industrial equipment
CREATE TABLE machines (
    machine_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    location VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Parameters table for machine sensors/measurements
CREATE TABLE parameters (
    parameter_id SERIAL PRIMARY KEY,
    machine_id INTEGER REFERENCES machines(machine_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    register_address VARCHAR(10) NOT NULL, -- D20, D21, etc.
    unit VARCHAR(10) NOT NULL,
    min_value DECIMAL(10,2),
    max_value DECIMAL(10,2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sensor data table for storing real-time measurements
CREATE TABLE sensor_data (
    data_id SERIAL PRIMARY KEY,
    parameter_id INTEGER REFERENCES parameters(parameter_id) ON DELETE CASCADE,
    value DECIMAL(10,2) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quality_code INTEGER DEFAULT 0 -- 0: good, 1: uncertain, 2: bad
);

-- User machine assignments for engineers
CREATE TABLE user_machine_assignments (
    assignment_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    machine_id INTEGER REFERENCES machines(machine_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, machine_id)
);

-- Alerts table for system notifications
CREATE TABLE alerts (
    alert_id SERIAL PRIMARY KEY,
    parameter_id INTEGER REFERENCES parameters(parameter_id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    threshold_value DECIMAL(10,2),
    actual_value DECIMAL(10,2),
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by INTEGER REFERENCES users(user_id),
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_sensor_data_parameter_timestamp ON sensor_data(parameter_id, timestamp DESC);
CREATE INDEX idx_alerts_parameter_created ON alerts(parameter_id, created_at DESC);
CREATE INDEX idx_user_machine_assignments_user ON user_machine_assignments(user_id);
CREATE INDEX idx_parameters_machine ON parameters(machine_id);

-- Insert default admin user (password: admin123)
INSERT INTO users (username, email, password_hash, role) VALUES 
('admin', 'admin@nextcare.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewBsWHNPfY1BHfNS', 'admin');

-- Insert sample machines
INSERT INTO machines (name, description, location) VALUES 
('Production Line A', 'Main production line for assembly', 'Factory Floor 1'),
('Packaging Unit B', 'Automated packaging system', 'Factory Floor 2'),
('Quality Control Station', 'Final quality inspection unit', 'QC Department');

-- Insert sample parameters for machine 1
INSERT INTO parameters (machine_id, name, register_address, unit, min_value, max_value) VALUES 
(1, 'Temperature', 'D20', '°C', 20.0, 80.0),
(1, 'Vibration', 'D21', 'Hz', 0.0, 100.0),
(1, 'Shock', 'D22', 'g', 0.0, 10.0),
(1, 'Oil Supply', 'D23', '%', 0.0, 100.0),
(1, 'Sound', 'D24', 'dB', 30.0, 90.0);

-- Insert sample parameters for machine 2
INSERT INTO parameters (machine_id, name, register_address, unit, min_value, max_value) VALUES 
(2, 'Temperature', 'D25', '°C', 18.0, 75.0),
(2, 'Pressure', 'D26', 'PSI', 0.0, 150.0),
(2, 'Speed', 'D27', 'RPM', 0.0, 3000.0);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_machines_updated_at BEFORE UPDATE ON machines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_parameters_updated_at BEFORE UPDATE ON parameters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();