#!/usr/bin/env python3
"""
Setup and test script for Suraksha Yatra AI Service
This script verifies MongoDB connection and tests AI endpoints
"""

import sys
import os
from datetime import datetime, timedelta
import traceback

def test_mongodb_connection():
    """Test MongoDB connection"""
    print("🔗 Testing MongoDB Connection...")
    
    try:
        from database.mongodb_client import MongoDBClient
        
        # Initialize client
        db_client = MongoDBClient()
        
        # Test connection by pinging the admin database
        admin_db = db_client.client.admin
        admin_db.command('ping')
        
        print("✅ MongoDB connection successful!")
        
        # Test database access
        collections = db_client.db.list_collection_names()
        print(f"✅ Connected to database: {db_client.db.name}")
        print(f"✅ Available collections: {collections}")
        
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {str(e)}")
        print(f"Error details: {traceback.format_exc()}")
        return False

def test_ai_models():
    """Test AI model initialization"""
    print("\n🤖 Testing AI Models...")
    
    try:
        from database.mongodb_client import MongoDBClient
        from ml_models.risk_predictor import RiskPredictor
        from ml_models.anomaly_detector import AnomalyDetector
        from ml_models.pattern_analyzer import PatternAnalyzer
        
        db_client = MongoDBClient()
        
        # Test Risk Predictor
        risk_predictor = RiskPredictor(db_client)
        print("✅ Risk Predictor initialized")
        
        # Test simple prediction
        test_route = {
            'start': {'lat': 28.6139, 'lng': 77.2090},
            'end': {'lat': 28.7041, 'lng': 77.1025}
        }
        
        risk_score = risk_predictor.predict_route_risk(test_route)
        print(f"✅ Risk Prediction test: {risk_score}")
        
        # Test Anomaly Detector
        anomaly_detector = AnomalyDetector(db_client)
        print("✅ Anomaly Detector initialized")
        
        # Test Pattern Analyzer
        pattern_analyzer = PatternAnalyzer(db_client)
        print("✅ Pattern Analyzer initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ AI model test failed: {str(e)}")
        print(f"Error details: {traceback.format_exc()}")
        return False

def test_flask_app():
    """Test Flask app startup"""
    print("\n🌐 Testing Flask App...")
    
    try:
        # Import and create app
        from app import app
        
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/health')
            
            if response.status_code == 200:
                print("✅ Flask app started successfully")
                print(f"✅ Health check: {response.json}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Flask app test failed: {str(e)}")
        print(f"Error details: {traceback.format_exc()}")
        return False

def main():
    """Main setup and test function"""
    print("🚀 Suraksha Yatra AI Service Setup & Test")
    print("=" * 50)
    
    # Check Python dependencies
    print("📦 Checking dependencies...")
    required_packages = [
        'flask', 'pymongo', 'numpy', 'scipy', 
        'geopy', 'python-dotenv', 'scikit-learn', 'pandas'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n❌ Missing packages: {missing_packages}")
        print("Please run: pip install -r requirements.txt")
        return False
    
    print("\n✅ All dependencies satisfied!")
    
    # Test MongoDB connection
    if not test_mongodb_connection():
        print("\n❌ Setup failed at MongoDB connection")
        return False
    
    # Test AI models
    if not test_ai_models():
        print("\n❌ Setup failed at AI model initialization")
        return False
    
    # Test Flask app
    if not test_flask_app():
        print("\n❌ Setup failed at Flask app test")
        return False
    
    print("\n🎉 All tests passed! AI Service is ready to run.")
    print("\nTo start the service:")
    print("python app.py")
    print("\nTo test with backend integration:")
    print("1. Start this AI service: python app.py")
    print("2. Start backend: cd ../backend && npm run dev")
    print("3. Test endpoints at: http://localhost:4000/api/ai/*")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)