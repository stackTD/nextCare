"""
Data Collection Module for NextCare Industrial Monitoring System

This module handles communication with PLC/mock sensor via Modbus TCP
and stores the collected data in the database.
"""

import time
import logging
import threading
from datetime import datetime
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException, ConnectionException
from sqlalchemy.exc import SQLAlchemyError
from app.models import Parameter, SensorData, Alert, db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataCollector:
    """Handles data collection from PLC via Modbus TCP"""
    
    def __init__(self, host='127.0.0.1', port=502, update_interval=5):
        self.host = host
        self.port = port
        self.update_interval = update_interval
        self.client = None
        self.running = False
        self.collection_thread = None
        
    def connect(self):
        """Establish connection to PLC"""
        try:
            self.client = ModbusTcpClient(host=self.host, port=self.port, timeout=10)
            connection = self.client.connect()
            
            if connection:
                logger.info(f"Successfully connected to PLC at {self.host}:{self.port}")
                return True
            else:
                logger.error(f"Failed to connect to PLC at {self.host}:{self.port}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to PLC: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from PLC"""
        if self.client:
            try:
                self.client.close()
                logger.info("Disconnected from PLC")
            except Exception as e:
                logger.error(f"Error disconnecting from PLC: {e}")
    
    def read_register(self, register_address):
        """Read a single register from PLC"""
        if not self.client or not self.client.connected:
            if not self.connect():
                return None
        
        try:
            # Extract register number from address (e.g., D20 -> 20)
            if isinstance(register_address, str) and register_address.startswith('D'):
                register_num = int(register_address[1:])
            else:
                register_num = int(register_address)
            
            # Read holding register
            result = self.client.read_holding_registers(register_num, 1, unit=1)
            
            if result.isError():
                logger.error(f"Modbus error reading register {register_address}: {result}")
                return None
            
            # Convert scaled value back to float (values are scaled by 100 in mock PLC)
            raw_value = result.registers[0]
            actual_value = raw_value / 100.0
            
            return actual_value
            
        except Exception as e:
            logger.error(f"Error reading register {register_address}: {e}")
            return None
    
    def collect_parameter_data(self, parameter):
        """Collect data for a single parameter"""
        try:
            value = self.read_register(parameter.register_address)
            
            if value is not None:
                # Create sensor data record
                sensor_data = SensorData(
                    parameter_id=parameter.parameter_id,
                    value=value,
                    timestamp=datetime.utcnow(),
                    quality_code=0  # 0 = good quality
                )
                
                db.session.add(sensor_data)
                
                # Check for alerts
                self.check_parameter_alerts(parameter, value)
                
                return True
            else:
                # Create bad quality record
                sensor_data = SensorData(
                    parameter_id=parameter.parameter_id,
                    value=0,
                    timestamp=datetime.utcnow(),
                    quality_code=2  # 2 = bad quality
                )
                
                db.session.add(sensor_data)
                logger.warning(f"Failed to read parameter {parameter.name} ({parameter.register_address})")
                return False
                
        except Exception as e:
            logger.error(f"Error collecting data for parameter {parameter.name}: {e}")
            return False
    
    def check_parameter_alerts(self, parameter, value):
        """Check if parameter value triggers any alerts"""
        try:
            alerts_created = []
            
            # Check min/max thresholds
            if parameter.min_value is not None and value < float(parameter.min_value):
                alert = Alert(
                    parameter_id=parameter.parameter_id,
                    message=f"{parameter.name} value ({value} {parameter.unit}) is below minimum threshold",
                    severity='high',
                    threshold_value=parameter.min_value,
                    actual_value=value
                )
                db.session.add(alert)
                alerts_created.append('minimum')
            
            if parameter.max_value is not None and value > float(parameter.max_value):
                alert = Alert(
                    parameter_id=parameter.parameter_id,
                    message=f"{parameter.name} value ({value} {parameter.unit}) exceeds maximum threshold",
                    severity='high',
                    threshold_value=parameter.max_value,
                    actual_value=value
                )
                db.session.add(alert)
                alerts_created.append('maximum')
            
            # Log alerts
            if alerts_created:
                logger.warning(f"Alerts created for {parameter.name}: {', '.join(alerts_created)}")
            
        except Exception as e:
            logger.error(f"Error checking alerts for parameter {parameter.name}: {e}")
    
    def collect_all_data(self):
        """Collect data for all active parameters"""
        try:
            # Get all active parameters
            parameters = Parameter.query.filter_by(is_active=True).all()
            
            if not parameters:
                logger.info("No active parameters found for data collection")
                return
            
            successful_reads = 0
            total_parameters = len(parameters)
            
            for parameter in parameters:
                try:
                    if self.collect_parameter_data(parameter):
                        successful_reads += 1
                except Exception as e:
                    logger.error(f"Error collecting data for parameter {parameter.name}: {e}")
            
            # Commit all changes
            db.session.commit()
            
            logger.info(f"Data collection cycle completed: {successful_reads}/{total_parameters} parameters successful")
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during data collection: {e}")
            db.session.rollback()
        except Exception as e:
            logger.error(f"Unexpected error during data collection: {e}")
            db.session.rollback()
    
    def collection_loop(self):
        """Main data collection loop"""
        logger.info(f"Starting data collection loop with {self.update_interval}s interval")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Collect data
                self.collect_all_data()
                
                # Calculate sleep time to maintain consistent interval
                elapsed_time = time.time() - start_time
                sleep_time = max(0, self.update_interval - elapsed_time)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"Data collection took {elapsed_time:.2f}s, longer than interval {self.update_interval}s")
                    
            except KeyboardInterrupt:
                logger.info("Data collection interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in data collection loop: {e}")
                time.sleep(self.update_interval)
    
    def start_collection(self):
        """Start the data collection in a separate thread"""
        if self.running:
            logger.warning("Data collection is already running")
            return
        
        self.running = True
        self.collection_thread = threading.Thread(target=self.collection_loop, daemon=True)
        self.collection_thread.start()
        logger.info("Data collection started")
    
    def stop_collection(self):
        """Stop the data collection"""
        if not self.running:
            logger.warning("Data collection is not running")
            return
        
        self.running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        
        self.disconnect()
        logger.info("Data collection stopped")
    
    def is_connected(self):
        """Check if connected to PLC"""
        return self.client and self.client.connected
    
    def get_status(self):
        """Get collector status information"""
        return {
            'running': self.running,
            'connected': self.is_connected(),
            'host': self.host,
            'port': self.port,
            'update_interval': self.update_interval
        }

# Global data collector instance
_data_collector = None

def get_data_collector():
    """Get the global data collector instance"""
    global _data_collector
    return _data_collector

def initialize_data_collector(host='127.0.0.1', port=502, update_interval=5):
    """Initialize the global data collector"""
    global _data_collector
    _data_collector = DataCollector(host=host, port=port, update_interval=update_interval)
    return _data_collector

def start_data_collection():
    """Start data collection if collector is initialized"""
    collector = get_data_collector()
    if collector:
        collector.start_collection()
    else:
        logger.error("Data collector not initialized")

def stop_data_collection():
    """Stop data collection if collector is running"""
    collector = get_data_collector()
    if collector:
        collector.stop_collection()
    else:
        logger.warning("Data collector not initialized")