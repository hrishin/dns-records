#!/bin/bash
# Integration test runner for DNS Records Manager

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}DNS Records Manager - Integration Test Runner${NC}"
echo "=================================================="

# Check if we're in the right directory
if [[ ! -f "$PROJECT_DIR/setup.py" ]]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

# Check if virtual environment exists
if [[ ! -d "$PROJECT_DIR/venv" ]]; then
    echo -e "${YELLOW}Virtual environment not found. Creating one...${NC}"
    python3 -m venv "$PROJECT_DIR/venv"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source "$PROJECT_DIR/venv/bin/activate"

# Install/upgrade dependencies
echo -e "${BLUE}Installing/upgrading dependencies...${NC}"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# Create test directories
echo -e "${BLUE}Setting up test environment...${NC}"
mkdir -p "$PROJECT_DIR/test_data"
mkdir -p "$PROJECT_DIR/test_reports"

# Set environment variables
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# Run integration tests
echo -e "${BLUE}Running integration tests...${NC}"
cd "$PROJECT_DIR"

echo -e "${GREEN}Running full integration test suite...${NC}"
behave -f pretty -v --outfile test_reports/integration_tests.txt


if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}All integration tests passed!${NC}"
    echo -e "${BLUE}Test report saved to: test_reports/integration_tests.txt${NC}"
else
    echo -e "${RED}Some integration tests failed. Check the output above.${NC}"
    exit 1
fi

# Generate test summary
echo -e "${BLUE}Generating test summary...${NC}"
if [[ -f "test_reports/integration_tests.txt" ]]; then
    echo "=== Test Summary ===" >> test_reports/summary.txt
    date >> test_reports/summary.txt
    echo "BIND Running: $BIND_RUNNING" >> test_reports/summary.txt
    echo "==================" >> test_reports/summary.txt
    echo -e "${GREEN}Test summary saved to: test_reports/summary.txt${NC}"
fi

echo -e "${GREEN}Integration test run completed!${NC}"
