# app/__init__.py
# This file makes the app directory a proper Python package
# and exposes the key components from app.py

# Import the Flask app and db objects for use in other modules
from app.app import app, db

# Import the models for use in other modules
from app.app import User, Article

# For simplified imports
__all__ = ['app', 'db', 'User', 'Article'] 