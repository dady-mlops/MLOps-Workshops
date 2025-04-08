#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Setting up environment for AI News Agency ===${NC}"

# Check for Python 3.10
if ! command -v python3.10 &> /dev/null; then
    echo -e "${RED}Python 3.10 not found.${NC}"
    echo -e "${YELLOW}To install Python 3.10, run:${NC}"
    echo -e "${GREEN}brew install python@3.10${NC}"
    echo -e "${YELLOW}After installing Python 3.10, run this script again.${NC}"
    exit 1
fi

# Display Python 3.10 version
python_version=$(python3.10 --version)
echo -e "${GREEN}Using: ${python_version}${NC}"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment with Python 3.10...${NC}"
    python3.10 -m venv .venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error creating virtual environment.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Virtual environment created.${NC}"
else
    echo -e "${GREEN}Virtual environment already exists.${NC}"
    echo -e "${YELLOW}If you want to create a new environment with Python 3.10, delete the existing one:${NC}"
    echo -e "${GREEN}rm -rf .venv${NC}"
    echo -e "${YELLOW}And run this script again.${NC}"
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

# Update pip
echo -e "${YELLOW}Updating pip to the latest version...${NC}"
python -m pip install --upgrade pip
if [ $? -ne 0 ]; then
    echo -e "${RED}Warning: Failed to update pip. Continuing with current version.${NC}"
else
    echo -e "${GREEN}Pip updated to the latest version.${NC}"
fi

# Install dependencies from requirements.txt
echo -e "${YELLOW}Installing dependencies from requirements.txt...${NC}"
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}Error installing dependencies.${NC}"
    exit 1
else
    echo -e "${GREEN}All dependencies successfully installed.${NC}"
fi

# Check installed packages
echo -e "${YELLOW}Installed packages:${NC}"
pip list

# Setup information
echo -e "\n${GREEN}Virtual environment with Python 3.10 activated and dependencies installed!${NC}"
echo -e "${YELLOW}To run the application, execute: ${GREEN}./run.sh${NC}"
echo -e "${YELLOW}Don't forget to configure the .env file with your API keys:${NC}"
echo -e "${GREEN}GOOGLE_API_KEY=your_google_api_key${NC}"
echo -e "${GREEN}GOOGLE_CSE_ID=your_search_engine_id${NC}"
echo -e "\n${YELLOW}To deactivate the virtual environment, use the command: ${GREEN}deactivate${NC}"
