#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Starting AI News Agency in Docker ===${NC}"

# Wait for PostgreSQL to be ready if using PostgreSQL
if [ "$DB_TYPE" = "postgres" ]; then
    echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
    
    # Wait for PostgreSQL to be ready
    until pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER; do
        echo -e "${YELLOW}PostgreSQL is unavailable - sleeping${NC}"
        sleep 1
    done
    
    echo -e "${GREEN}PostgreSQL is ready!${NC}"
    
    # Give PostgreSQL a moment to fully initialize
    sleep 2
fi

# Initialize the database
echo -e "${YELLOW}Initializing database...${NC}"
python init_db.py
echo -e "${GREEN}Database initialized successfully${NC}"

# Start the application with Gunicorn
echo -e "${YELLOW}Starting application with Gunicorn...${NC}"
echo -e "${GREEN}Application will be available at: http://0.0.0.0:5000${NC}"

# Start Gunicorn with specified parameters
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 120 app:app
