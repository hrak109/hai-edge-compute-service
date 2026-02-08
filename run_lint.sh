#!/bin/bash

# Define colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔍 Running Lint Tests...${NC}"

cd edge_compute_server || { echo -e "${RED}❌ Directory 'edge_compute_server' not found!${NC}"; exit 1; }

# check if venv exists
VENV_PYTHON=""
if [ -d "venv" ]; then
    VENV_PYTHON="./venv/bin/python3"
elif [ -d "../venv" ]; then
    VENV_PYTHON="../venv/bin/python3"
else
    echo -e "${RED}❌ No virtual environment found!${NC}"
    exit 1
fi

echo "Using Python: $VENV_PYTHON"

# Install flake8 if needed
if ! $VENV_PYTHON -m flake8 --version &> /dev/null; then
    echo "📦 Installing flake8..."
    $VENV_PYTHON -m pip install flake8
fi

# Run flake8
$VENV_PYTHON -m flake8 .
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✅ Lint Tests Passed!${NC}"
else
    echo -e "${RED}❌ Lint Tests Failed!${NC}"
fi

exit $exit_code
