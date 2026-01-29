#!/bin/bash

# Install all backend dependencies for Instructor Assistant

cd "$(dirname "$0")"

echo "📦 Installing backend dependencies..."

# Activate virtual environment
source backend/.webenv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install all requirements
pip install -r backend/requirements.txt

# Install playwright browsers (for web scraping features)
echo ""
echo "🌐 Installing Playwright browsers..."
playwright install chromium

echo ""
echo "✅ All dependencies installed successfully!"
echo ""
echo "Run ./start.sh to start the application"
