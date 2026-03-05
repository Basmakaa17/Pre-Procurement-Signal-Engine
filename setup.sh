#!/bin/bash

# Publicus Signal Engine - Master Setup Script
# This script sets up the entire project for local development

set -e  # Exit on error

echo "=========================================="
echo "Publicus Signal Engine - Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo -e "${RED}Error: Python 3.11 or higher is required. Found Python $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python $PYTHON_VERSION detected${NC}"
echo ""

# Backend setup
echo "=========================================="
echo "Backend Setup"
echo "=========================================="

cd backend

# Create .env from .env.example if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit backend/.env and add your credentials${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment and install requirements
echo "Installing backend dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Backend dependencies installed${NC}"

deactivate
cd ..

echo ""

# Frontend setup
echo "=========================================="
echo "Frontend Setup"
echo "=========================================="

cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Frontend dependencies already installed${NC}"
fi

# Create .env.local from .env.local.example if it doesn't exist
if [ ! -f .env.local ]; then
    if [ -f .env.local.example ]; then
        echo "Creating .env.local from .env.local.example..."
        cp .env.local.example .env.local
        echo -e "${GREEN}✓ .env.local created${NC}"
    fi
fi

cd ..

echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. Configure Backend (.env):"
echo "   - Add SUPABASE_URL from your Supabase project settings"
echo "   - Add SUPABASE_ANON_KEY from Supabase API settings"
echo "   - Add SUPABASE_SERVICE_KEY from Supabase API settings (⚠️  keep secret!)"
echo "   - Add ANTHROPIC_API_KEY from https://console.anthropic.com/"
echo ""
echo "2. Set up Database:"
echo "   - Open Supabase SQL Editor"
echo "   - Run: backend/database/complete_schema.sql"
echo "   - Run: backend/database/seed_taxonomies.sql"
echo ""
echo "3. Run Backend:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --reload --port 8000"
echo ""
echo "4. Run Frontend (in a new terminal):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "5. Access the application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "6. Run the Pipeline (to fetch and classify grants):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python -m app.intelligence.signal_detector"
echo ""
echo "7. Deployment:"
echo ""
echo "   Railway (Backend):"
echo "   - Create a new project on Railway"
echo "   - Connect your GitHub repository"
echo "   - Add environment variables from backend/.env"
echo "   - Railway will auto-detect Python and deploy"
echo ""
echo "   Vercel (Frontend):"
echo "   - Import your GitHub repository to Vercel"
echo "   - Set framework preset to Next.js"
echo "   - Add environment variable: NEXT_PUBLIC_API_URL = your Railway backend URL"
echo "   - Deploy"
echo ""
echo "=========================================="
