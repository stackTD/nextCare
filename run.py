#!/usr/bin/env python3
"""
NextCare Industrial Monitoring System
Main application entry point
"""

import os
import sys
import signal
import logging
from flask import Flask
from app import create_app, socketio
from app.data_collector import initialize_data_collector, start_data_collection, stop_data_collection
from app.models import db
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nextcare.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def create_tables(app):
    """Create database tables if they don't exist"""
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down...")
    stop_data_collection()
    sys.exit(0)

def main():
    """Main application function"""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create Flask application
    app = create_app()
    
    # Create database tables
    create_tables(app)
    
    # Initialize data collector
    config = app.config
    collector = initialize_data_collector(
        host=config.get('PLC_HOST', '127.0.0.1'),
        port=config.get('PLC_PORT', 502),
        update_interval=config.get('DATA_COLLECTION_INTERVAL', 5)
    )
    
    # Start data collection in development mode
    if app.config.get('DEBUG', False):
        logger.info("Starting data collection in debug mode")
        start_data_collection()
    
    # Get host and port from environment or use defaults
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Starting NextCare application on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    
    try:
        # Run the application with SocketIO
        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug,
            use_reloader=False  # Disable reloader to prevent duplicate data collection
        )
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Error running application: {e}")
    finally:
        # Clean shutdown
        stop_data_collection()
        logger.info("NextCare application shutdown complete")

if __name__ == '__main__':
    main()