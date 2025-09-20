#!/bin/bash
# Build script for Render deployment - Python 3.11 only

echo "Starting AI service build with Python 3.11..."

# Check Python version
python --version

# Upgrade build tools to specific Python 3.11 compatible versions
pip install --upgrade pip==23.1.2 setuptools==67.8.0 wheel==0.40.0

# Install dependencies
pip install -r requirements.txt

echo "Build completed successfully!"