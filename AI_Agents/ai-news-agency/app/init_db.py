#!/usr/bin/env python3
"""
Script for initializing PostgreSQL database.
Creates tables and default administrator.
"""

import os
import logging
from app.app import app, db, User, Article

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initializes database by creating tables and default administrator."""
    with app.app_context():
        # Create all tables
        db.create_all()
        logger.info("Database tables created successfully")
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin')  # Change this in production!
            db.session.add(admin)
            db.session.commit()
            logger.info("Default admin user created")
        else:
            logger.info("Admin user already exists")
            
        logger.info("Database initialization completed")

if __name__ == "__main__":
    init_database()
