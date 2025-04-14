# app/models.py
# This file re-exports models from app.py to allow proper importing

# Import the database models from app.py
from app.app import User, Article, db

# For simplified imports
__all__ = ['User', 'Article', 'db'] 