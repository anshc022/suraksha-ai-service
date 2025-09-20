#!/bin/bash
# Build script for Render deployment

echo "Starting AI service build..."

# Upgrade pip first
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

echo "Build completed successfully!"