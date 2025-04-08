#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Starting AI News Agency ===${NC}"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}Virtual environment not found. Please run ./setup.sh first${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}Error activating virtual environment.${NC}"
    exit 1
fi
echo -e "${GREEN}Virtual environment activated.${NC}"

# Check if required files exist
if [ ! -f "app.py" ]; then
    echo -e "${RED}File app.py not found. Make sure you are in the project root directory.${NC}"
    exit 1
fi

# Start the application
echo -e "${YELLOW}Starting Flask application...${NC}"
echo -e "${GREEN}Application will be available at: http://localhost:5000${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Run with error handling
python app.py
if [ $? -ne 0 ]; then
    echo -e "${RED}An error occurred while starting the application.${NC}"
    echo -e "${YELLOW}Check that all dependencies are installed correctly.${NC}"
    exit 1
fi

# Deactivate virtual environment on exit
deactivate
