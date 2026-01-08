#!/bin/bash
# DeepTrender - One-Command Local Setup Script
# Usage: ./setup.sh

set -e  # Exit on error

echo "=========================================="
echo "🔬 DeepTrender - Local Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo "📌 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python version: $PYTHON_VERSION"

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo -e "${RED}❌ Python 3.11+ required${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python version OK${NC}"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠️  Virtual environment already exists${NC}"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
python -m pip install --upgrade pip -q

# Install dependencies
echo "📦 Installing dependencies..."
echo "   This may take 5-10 minutes for first-time setup..."
pip install -r requirements.txt -q

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${RED}❌ Dependency installation failed${NC}"
    exit 1
fi
echo ""

# Create required directories
echo "📁 Creating required directories..."
mkdir -p data output/figures output/reports
touch data/.gitkeep output/figures/.gitkeep output/reports/.gitkeep
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Initialize database (will be created on first run)
echo "🗄️  Database will be initialized on first run"
if [ -f "data/keywords.db" ]; then
    DB_SIZE=$(du -h data/keywords.db | cut -f1)
    echo "   Existing database found: $DB_SIZE"
fi
echo ""

# Run tests
echo "🧪 Running tests..."
pytest -q --tb=short

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed${NC}"
else
    echo -e "${YELLOW}⚠️  Some tests failed (check output above)${NC}"
fi
echo ""

# Display summary
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "📋 Next Steps:"
echo ""
echo "1️⃣  Activate environment:"
echo "   source venv/bin/activate"
echo ""
echo "2️⃣  Run pipeline (test with small limit):"
echo "   python src/main.py --source arxiv --arxiv-days 1 --limit 10"
echo ""
echo "3️⃣  Run full pipeline:"
echo "   python src/main.py"
echo ""
echo "4️⃣  Start web server:"
echo "   python src/web/app.py"
echo "   Visit: http://localhost:5000"
echo ""
echo "5️⃣  Run tests:"
echo "   pytest -v"
echo ""
echo "=========================================="
