#!/bin/bash

# Define colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Local Tests for Edge Compute Server...${NC}"

# Navigate to the server directory
cd edge_compute_server || { echo -e "${RED}❌ Directory 'edge_compute_server' not found!${NC}"; exit 1; }

# check if venv exists and activate it
if [ -d "venv" ]; then
    echo "Using virtual environment..."
    source venv/bin/activate
elif [ -d "../venv" ]; then
    echo "Using parent virtual environment..."
    source ../venv/bin/activate
else
    echo "⚠️  No virtual environment found. Running with system python..."
fi

# Install test dependencies if needed (pytest)
if ! command -v pytest &> /dev/null; then
    echo "📦 Installing test dependencies..."
    pip install pytest
fi

# Run pytest
echo "🧪 Running Tests..."
python3 -m pytest tests/ -v

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✅ All Tests Passed!${NC}"
else
    echo -e "${RED}❌ Tests Failed!${NC}"
fi

exit $exit_code
