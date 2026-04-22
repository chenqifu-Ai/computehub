#!/bin/bash
# ComputeHub - Environment Setup Script

set -e

echo "🚀 ComputeHub Setup Script"
echo "=========================="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.10"

echo "📌 Checking Python version..."
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python 3.10+ required, found $PYTHON_VERSION"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION detected"

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create .env file from example
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# ComputeHub Configuration
DATABASE_URL=postgresql://computehub:computehub_secret@localhost:5432/computehub
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-this-in-production-$(openssl rand -hex 32)
DEBUG=true
EOF
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backend/logs
mkdir -p node/logs

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start dependencies: docker-compose up -d postgres redis"
echo "2. Start backend: uvicorn backend.main:app --reload"
echo "3. Start worker: celery -A backend.workers.tasks worker --loglevel=info"
echo "4. Open API docs: http://localhost:8000/docs"
