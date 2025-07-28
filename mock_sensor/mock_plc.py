#!/usr/bin/env python3
"""
Mock PLC Sensor Simulator for NextCare Industrial Monitoring System

This simulator acts as a PLC device that generates realistic sensor data
and serves it via Modbus TCP protocol. It simulates 5 different parameters:
- D20: Temperature (°C)
- D21: Vibration (Hz)
- D22: Shock (g)
- D23: Oil Supply (%)
- D24: Sound (dB)
"""

import time
import random
import math
import logging
import threading
from datetime import datetime
from pymodbus.server.sync import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SensorSimulator:
    """Simulates realistic sensor data with variations and patterns"""
    
    def __init__(self):
        self.base_values = {
            20: 25.0,  # D20: Temperature base 25°C
            21: 50.0,  # D21: Vibration base 50Hz
            22: 2.0,   # D22: Shock base 2g
            23: 85.0,  # D23: Oil Supply base 85%
            24: 60.0   # D24: Sound base 60dB
        }
        
        # Simulation parameters
        self.variations = {
            20: {'amplitude': 10.0, 'frequency': 0.1, 'noise': 2.0},  # Temperature
            21: {'amplitude': 15.0, 'frequency': 0.2, 'noise': 5.0},  # Vibration
            22: {'amplitude': 1.5, 'frequency': 0.3, 'noise': 0.5},   # Shock
            23: {'amplitude': 10.0, 'frequency': 0.05, 'noise': 3.0}, # Oil Supply
            24: {'amplitude': 8.0, 'frequency': 0.15, 'noise': 4.0}   # Sound
        }
        
        self.start_time = time.time()
        
    def get_value(self, register):
        """Generate realistic sensor value with sine wave + noise"""
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        base = self.base_values[register]
        variation = self.variations[register]
        
        # Generate sine wave pattern
        sine_component = variation['amplitude'] * math.sin(variation['frequency'] * elapsed)
        
        # Add random noise
        noise_component = random.uniform(-variation['noise'], variation['noise'])
        
        # Calculate final value
        value = base + sine_component + noise_component
        
        # Apply realistic constraints
        if register == 20:  # Temperature: 20-80°C
            value = max(20.0, min(80.0, value))
        elif register == 21:  # Vibration: 0-100Hz
            value = max(0.0, min(100.0, value))
        elif register == 22:  # Shock: 0-10g
            value = max(0.0, min(10.0, value))
        elif register == 23:  # Oil Supply: 0-100%
            value = max(0.0, min(100.0, value))
        elif register == 24:  # Sound: 30-90dB
            value = max(30.0, min(90.0, value))
        
        return round(value, 2)

class MockPLCServer:
    """Mock PLC server using Modbus TCP protocol"""
    
    def __init__(self, host='127.0.0.1', port=502):
        self.host = host
        self.port = port
        self.sensor_simulator = SensorSimulator()
        self.running = False
        
        # Initialize Modbus data store
        # We'll use holding registers starting from address 20 (D20, D21, etc.)
        self.store = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [0]*100),  # Discrete Inputs
            co=ModbusSequentialDataBlock(0, [0]*100),  # Coils
            hr=ModbusSequentialDataBlock(0, [0]*100),  # Holding Registers
            ir=ModbusSequentialDataBlock(0, [0]*100)   # Input Registers
        )
        
        self.context = ModbusServerContext(slaves=self.store, single=True)
        
        # Set device identification
        self.identity = ModbusDeviceIdentification()
        self.identity.VendorName = 'NextCare Systems'
        self.identity.ProductCode = 'NC-MOCK-PLC'
        self.identity.VendorUrl = 'http://nextcare.com'
        self.identity.ProductName = 'Mock PLC Sensor Simulator'
        self.identity.ModelName = 'NC-PLC-SIM-v1.0'
        self.identity.MajorMinorRevision = '1.0'
        
    def update_sensor_data(self):
        """Continuously update sensor data in the Modbus registers"""
        logger.info("Starting sensor data simulation...")
        
        while self.running:
            try:
                # Update each sensor register
                for register in [20, 21, 22, 23, 24]:
                    value = self.sensor_simulator.get_value(register)
                    # Convert float to integer (multiply by 100 to preserve 2 decimal places)
                    scaled_value = int(value * 100)
                    self.store.setValues(3, register, [scaled_value])  # Function code 3 = holding registers
                
                # Log current values every 30 seconds
                if int(time.time()) % 30 == 0:
                    values = {}
                    for register in [20, 21, 22, 23, 24]:
                        raw_value = self.store.getValues(3, register, count=1)[0]
                        values[f'D{register}'] = raw_value / 100.0
                    
                    logger.info(f"Current sensor values: {values}")
                
                time.sleep(1)  # Update every second
                
            except Exception as e:
                logger.error(f"Error updating sensor data: {e}")
                time.sleep(5)
    
    def start(self):
        """Start the mock PLC server"""
        self.running = True
        
        # Start sensor data update thread
        sensor_thread = threading.Thread(target=self.update_sensor_data, daemon=True)
        sensor_thread.start()
        
        logger.info(f"Starting Mock PLC Server on {self.host}:{self.port}")
        logger.info("Register mapping:")
        logger.info("  D20 (Register 20): Temperature (°C) - scaled by 100")
        logger.info("  D21 (Register 21): Vibration (Hz) - scaled by 100")
        logger.info("  D22 (Register 22): Shock (g) - scaled by 100")
        logger.info("  D23 (Register 23): Oil Supply (%) - scaled by 100")
        logger.info("  D24 (Register 24): Sound (dB) - scaled by 100")
        logger.info("Values are scaled by 100 to preserve decimal precision in integer registers")
        
        try:
            # Start Modbus TCP server
            StartTcpServer(
                context=self.context,
                identity=self.identity,
                address=(self.host, self.port),
                framer=ModbusRtuFramer
            )
        except KeyboardInterrupt:
            logger.info("Shutting down Mock PLC Server...")
            self.running = False
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            self.running = False

def main():
    """Main function to run the mock PLC server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NextCare Mock PLC Sensor Simulator')
    parser.add_argument('--host', default='127.0.0.1', help='Server host address')
    parser.add_argument('--port', type=int, default=502, help='Server port')
    
    args = parser.parse_args()
    
    # Create and start the mock PLC server
    server = MockPLCServer(host=args.host, port=args.port)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down Mock PLC Server...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()