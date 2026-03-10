#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

echo "==> Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo "Python3 not found. Please install Python 3.11+."
    exit 1
fi

echo "==> Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

echo "==> Activating virtual environment..."
source .venv/bin/activate

echo "==> Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements/dev.txt -q

echo "==> Setting up .env..."
if [ ! -f "settings/.env" ]; then
    cp settings/.env.example settings/.env
    echo "Created settings/.env from .env.example. Fill in your values if needed."
fi

echo "==> Running migrations..."
python manage.py migrate

echo "==> Compiling translations..."
python manage.py compilemessages

echo "==> Starting development server..."
python manage.py runserver