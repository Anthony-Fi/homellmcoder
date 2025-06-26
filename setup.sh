
#!/bin/bash

# Stop on first error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print section headers
print_header() {
    echo -e "\n${GREEN}=== $1 ===${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
print_header "Checking Python version"
if ! command_exists python3; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.9 or higher.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "Found Python ${GREEN}${PYTHON_VERSION}${NC}"

# Create virtual environment
VENV_PATH="./venv"
print_header "Setting up virtual environment"

if [ -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}Virtual environment already exists at $VENV_PATH${NC}"
    read -p "Do you want to recreate it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_PATH"
    else
        echo -e "${GREEN}Using existing virtual environment${NC}"
        source "$VENV_PATH/bin/activate"
        goto activate_env
    fi
fi

echo "Creating virtual environment at $VENV_PATH"
python3 -m venv "$VENV_PATH"

if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}Failed to create virtual environment${NC}"
    exit 1
fi

# Activate the virtual environment
source "$VENV_PATH/bin/activate"

:activate_env
# Upgrade pip
print_header "Upgrading build tools"
python -m pip install --upgrade pip setuptools wheel

# Install requirements
print_header "Installing Python dependencies"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo -e "${YELLOW}requirements.txt not found. No Python dependencies to install.${NC}"
fi

# Install development dependencies if requirements-dev.txt exists
if [ -f "requirements-dev.txt" ]; then
    print_header "Installing development dependencies"
    pip install -r requirements-dev.txt
fi

# Install Node.js dependencies if package.json exists
if [ -f "package.json" ]; then
    print_header "Installing Node.js dependencies"
    if command_exists npm; then
        npm install
    else
        echo -e "${YELLOW}npm not found. Skipping Node.js dependencies.${NC}"
    fi
fi

echo -e "\n${GREEN}=== Setup complete! ===${NC}"
echo -e "\nTo activate the virtual environment in the future, run:"
echo -e "  ${GREEN}source $VENV_PATH/bin/activate${NC}"
echo -e "\nTo deactivate, simply type 'deactivate'"

# Make the script executable
chmod +x "$0"
