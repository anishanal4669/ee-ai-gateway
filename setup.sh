#!/bin/bash

# Enterprise AI Gateway - Setup Script
# Run this script to quickly setup the gateway

set -e

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║          ENTERPRISE AI GATEWAY - SETUP SCRIPT                              ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "${BLUE}[1/6]${NC} Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "  Found Python: $PYTHON_VERSION"

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    echo "${YELLOW}⚠️  Warning: Python 3.9+ is required, but $(python3 --version 2>&1) detected${NC}"
fi
echo ""

# Create virtual environment
echo "${BLUE}[2/6]${NC} Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✓ Virtual environment created"
else
    echo "  ✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "${BLUE}[3/6]${NC} Activating virtual environment..."
source venv/bin/activate
echo "  ✓ Virtual environment activated"
echo ""

# Install dependencies
echo "${BLUE}[4/6]${NC} Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -q -r requirements.txt
echo "  ✓ Dependencies installed"
echo ""

# Setup environment file
echo "${BLUE}[5/6]${NC} Setting up configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  ✓ Created .env file (review and update with your settings)"
else
    echo "  ✓ .env file already exists"
fi
echo ""

# Create logs directory
echo "${BLUE}[6/6]${NC} Creating logs directory..."
mkdir -p logs
echo "  ✓ Logs directory created"
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "${GREEN}✓ SETUP COMPLETE!${NC}"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Review configuration (optional):"
echo "   cat .env"
echo ""
echo "2. Run tests:"
echo "   pytest tests/ -v"
echo ""
echo "3. Start the gateway:"
echo "   python main.py"
echo ""
echo "4. Generate a token (in another terminal):"
echo "   curl -X POST http://localhost:8000/auth/token \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"username\":\"advisor@wealth.com\",\"lob\":\"wealth\",\"models\":[\"gpt-4\"],\"rate_limit\":100}'"
echo ""
echo "5. Send a prompt:"
echo "   curl -X POST http://localhost:8000/gateway/prompt \\"
echo "     -H 'Authorization: Bearer <TOKEN>' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"prompt\":\"Analyze portfolio\",\"model\":\"gpt-4\"}'"
echo ""
echo "📚 Documentation:"
echo "   - README.md         → Project overview"
echo "   - QUICKSTART.md     → 5-minute quick start"
echo "   - ARCHITECTURE.md   → Technical deep dive"
echo ""
echo "🚀 API Documentation:"
echo "   http://localhost:8000/docs (Swagger UI)"
echo "   http://localhost:8000/redoc (ReDoc)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
