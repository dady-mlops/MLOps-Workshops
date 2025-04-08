#!/usr/bin/env python3
"""
Script for initializing PostgreSQL database.
Creates tables and default administrator.
"""

import os
import logging
from app import app, db, User, create_default_admin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_db")

def init_database():
    """Initializes the database by creating tables and default administrator."""
    try:
        with app.app_context():
            logger.info("Creating database tables...")
            db.create_all()
            logger.info("Database tables created successfully")
            
            logger.info("Creating default admin user...")
            create_default_admin()
            logger.info("Default admin user created successfully")
            
            # Check that the user has been created
            admin = User.query.filter_by(username=os.getenv('DEFAULT_ADMIN_USERNAME', 'admin')).first()
            if admin:
                logger.info(f"Admin user '{admin.username}' exists")
            else:
                logger.warning("Admin user was not created")
                
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

if __name__ == "__main__":
    init_database()
