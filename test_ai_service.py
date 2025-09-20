import requests
import json
from datetime import datetime, timedelta

# AI Service URL
AI_SERVICE_URL = "http://localhost:5000"

def test_risk_prediction():
    """Test route risk prediction"""
    print("Testing Risk Prediction...")
    
    payload = {
        "route": {
            "start": {"lat": 28.6139, "lng": 77.2090},  # New Delhi
            "end": {"lat": 28.7041, "lng": 77.1025}      # Delhi Airport
        },
        "time_of_day": "evening",
        "user_id": "test_user_123"
    }
    
    try:
        response = requests.post(f"{AI_SERVICE_URL}/api/risk/predict", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Risk Score: {result['risk_score']}")
            print(f"✅ Risk Level: {result['risk_level']}")
            print(f"✅ Recommendations: {result['recommendations']}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def test_anomaly_detection():
    """Test anomaly detection"""
    print("\nTesting Anomaly Detection...")
    
    # Create sample location data with potential anomaly (high speed)
    payload = {
        "user_id": "test_user_123",
        "location_data": [
            {
                "lat": 28.6139,
                "lng": 77.2090,
                "timestamp": "2023-01-01T10:00:00Z",
                "speed": 25.5
            },
            {
                "lat": 28.6200,
                "lng": 77.2150,
                "timestamp": "2023-01-01T10:01:00Z",
                "speed": 150.0  # Potentially anomalous speed
            },
            {
                "lat": 28.6300,
                "lng": 77.2200,
                "timestamp": "2023-01-01T10:02:00Z",
                "speed": 30.0
            }
        ]
    }
    
    try:
        response = requests.post(f"{AI_SERVICE_URL}/api/anomaly/detect", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Is Anomaly: {result['is_anomaly']}")
            print(f"✅ Confidence: {result['confidence_score']}")
            print(f"✅ Type: {result.get('anomaly_type', 'None')}")
            print(f"✅ Details: {result.get('details', 'None')}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def test_pattern_analysis():
    """Test pattern analysis"""
    print("\nTesting Pattern Analysis...")
    
    payload = {
        "area": {
            "center": {"lat": 28.6139, "lng": 77.2090},
            "radius_km": 5.0
        },
        "time_range": {
            "start": (datetime.now() - timedelta(days=30)).isoformat(),
            "end": datetime.now().isoformat()
        },
        "incident_types": ["crime", "accident"]
    }
    
    try:
        response = requests.post(f"{AI_SERVICE_URL}/api/patterns/analyze", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Hotspots Found: {len(result['hotspots'])}")
            print(f"✅ Trends: {json.dumps(result['trends'], indent=2)}")
            print(f"✅ Risk Zones: {len(result['risk_zones'])}")
            print(f"✅ Insights: {len(result['insights'])}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def test_threat_assessment():
    """Test threat assessment"""
    print("\nTesting Threat Assessment...")
    
    payload = {
        "location": {"lat": 28.6139, "lng": 77.2090},
        "user_profile": {
            "age_group": "adult",
            "gender": "female",
            "travel_mode": "walking"
        },
        "context": {
            "time_of_day": "night",
            "day_of_week": "saturday",
            "weather": "clear"
        }
    }
    
    try:
        response = requests.post(f"{AI_SERVICE_URL}/api/threat/assess", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Threat Level: {result['threat_level']}")
            print(f"✅ Threat Score: {result['threat_score']}")
            print(f"✅ Contributing Factors: {result['contributing_factors']}")
            print(f"✅ Recommendations: {result['recommendations']}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def test_health_check():
    """Test health check"""
    print("\nTesting Health Check...")
    
    try:
        response = requests.get(f"{AI_SERVICE_URL}/health")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Service Status: {result['status']}")
            print(f"✅ Service: {result['service']}")
            print(f"✅ Timestamp: {result['timestamp']}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    print("🧪 Testing AI Service Endpoints\n")
    
    # Test all endpoints
    test_health_check()
    test_risk_prediction()
    test_anomaly_detection()
    test_pattern_analysis()
    test_threat_assessment()
    
    print("\n🏁 Testing Complete!")
    print("\nTo start the AI service:")
    print("1. cd ai-service")
    print("2. pip install -r requirements.txt")
    print("3. python app.py")
    print("\nTo test backend integration:")
    print("1. cd backend")
    print("2. npm install")
    print("3. npm run dev")
    print("4. Test endpoints at http://localhost:4000/api/ai/*")