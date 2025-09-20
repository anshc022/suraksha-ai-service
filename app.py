from flask import Flask, request, jsonify
import logging
from datetime import datetime, timedelta
import numpy as np
from database.mongodb_client import MongoDBClient
from ml_models.risk_predictor import RiskPredictor
from ml_models.anomaly_detector import AnomalyDetector
from ml_models.pattern_analyzer import PatternAnalyzer
import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize services
db_client = MongoDBClient()
risk_predictor = RiskPredictor(db_client)
anomaly_detector = AnomalyDetector(db_client)
pattern_analyzer = PatternAnalyzer(db_client)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'ai-ml-engine'
    })

@app.route('/api/risk/predict', methods=['POST'])
def predict_route_risk():
    """
    Predict route safety score based on historical data
    Expected payload: {
        "route": {
            "start": {"lat": float, "lng": float},
            "end": {"lat": float, "lng": float},
            "waypoints": [{"lat": float, "lng": float}] (optional)
        },
        "time_of_day": "morning|afternoon|evening|night" (optional),
        "user_id": string (optional)
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'route' not in data:
            return jsonify({'error': 'Route data is required'}), 400
        
        route = data['route']
        time_of_day = data.get('time_of_day', 'day')
        user_id = data.get('user_id')
        
        # Validate route data
        if not all(key in route for key in ['start', 'end']):
            return jsonify({'error': 'Start and end coordinates are required'}), 400
        
        # Predict risk score
        risk_score = risk_predictor.predict_route_risk(
            route=route,
            time_of_day=time_of_day,
            user_id=user_id
        )
        
        return jsonify({
            'risk_score': risk_score,
            'risk_level': _get_risk_level(risk_score),
            'recommendations': _get_risk_recommendations(risk_score),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in route risk prediction: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/anomaly/detect', methods=['POST'])
def detect_anomaly():
    """
    Detect unusual movement patterns
    Expected payload: {
        "user_id": string,
        "location_data": [
            {
                "lat": float,
                "lng": float,
                "timestamp": "ISO string",
                "speed": float (optional),
                "accuracy": float (optional)
            }
        ]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data or 'location_data' not in data:
            return jsonify({'error': 'User ID and location data are required'}), 400
        
        user_id = data['user_id']
        location_data = data['location_data']
        
        if not location_data or len(location_data) < 2:
            return jsonify({'error': 'At least 2 location points are required'}), 400
        
        # Detect anomalies
        anomaly_result = anomaly_detector.detect_anomalies(
            user_id=user_id,
            location_data=location_data
        )
        
        return jsonify({
            'is_anomaly': anomaly_result['is_anomaly'],
            'confidence_score': anomaly_result['confidence'],
            'anomaly_type': anomaly_result.get('type'),
            'details': anomaly_result.get('details'),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in anomaly detection: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/patterns/analyze', methods=['POST'])
def analyze_patterns():
    """
    Analyze incident patterns and identify hotspots
    Expected payload: {
        "area": {
            "center": {"lat": float, "lng": float},
            "radius_km": float
        },
        "time_range": {
            "start": "ISO string",
            "end": "ISO string"
        },
        "incident_types": ["accident", "crime", "medical"] (optional)
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'area' not in data:
            return jsonify({'error': 'Area data is required'}), 400
        
        area = data['area']
        time_range = data.get('time_range', {
            'start': (datetime.utcnow() - timedelta(days=30)).isoformat(),
            'end': datetime.utcnow().isoformat()
        })
        incident_types = data.get('incident_types')
        
        # Analyze patterns
        pattern_result = pattern_analyzer.analyze_patterns(
            area=area,
            time_range=time_range,
            incident_types=incident_types
        )
        
        return jsonify({
            'hotspots': pattern_result['hotspots'],
            'trends': pattern_result['trends'],
            'risk_zones': pattern_result['risk_zones'],
            'insights': pattern_result['insights'],
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in pattern analysis: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/threat/assess', methods=['POST'])
def assess_threat():
    """
    Assess threat level for a specific location and time
    Expected payload: {
        "location": {"lat": float, "lng": float},
        "user_profile": {
            "age_group": "young|adult|senior" (optional),
            "gender": "male|female|other" (optional),
            "travel_mode": "walking|driving|public_transport" (optional)
        },
        "context": {
            "time_of_day": "morning|afternoon|evening|night",
            "day_of_week": "monday|tuesday|..." (optional),
            "weather": "clear|rainy|foggy" (optional)
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'location' not in data:
            return jsonify({'error': 'Location data is required'}), 400
        
        location = data['location']
        user_profile = data.get('user_profile', {})
        context = data.get('context', {})
        
        # Assess threat level
        threat_assessment = _assess_threat_level(
            location=location,
            user_profile=user_profile,
            context=context
        )
        
        return jsonify({
            'threat_level': threat_assessment['level'],
            'threat_score': threat_assessment['score'],
            'contributing_factors': threat_assessment['factors'],
            'recommendations': threat_assessment['recommendations'],
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in threat assessment: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def _get_risk_level(score):
    """Convert numeric risk score to categorical level"""
    if score < 25:
        return 'low'
    elif score < 50:
        return 'moderate'
    elif score < 75:
        return 'high'
    else:
        return 'critical'

def _get_risk_recommendations(score):
    """Get safety recommendations based on risk score"""
    if score < 25:
        return ['Maintain normal safety awareness', 'Keep emergency contacts updated']
    elif score < 50:
        return ['Stay alert', 'Share your location with trusted contacts', 'Avoid isolated areas']
    elif score < 75:
        return ['Consider alternative routes', 'Travel in groups if possible', 'Inform others of your plans']
    else:
        return ['Strongly consider avoiding this route', 'Use alternative transportation', 'Contact local authorities if necessary']

def _assess_threat_level(location, user_profile, context):
    """
    Basic threat level assessment combining multiple factors
    This is a simplified MVP implementation
    """
    base_score = 20  # Base threat score
    factors = []
    
    # Time-based risk factors
    time_of_day = context.get('time_of_day', 'day')
    if time_of_day in ['night', 'late_evening']:
        base_score += 15
        factors.append('Late hour increases risk')
    elif time_of_day == 'evening':
        base_score += 8
        factors.append('Evening hours have moderate risk')
    
    # Weather-based factors
    weather = context.get('weather')
    if weather in ['rainy', 'foggy']:
        base_score += 10
        factors.append('Poor weather conditions')
    
    # Get historical incident data for the location
    # This would integrate with the pattern analyzer
    
    # Determine level
    if base_score < 30:
        level = 'low'
        recommendations = ['Normal safety precautions']
    elif base_score < 50:
        level = 'moderate'
        recommendations = ['Increased awareness recommended', 'Share location with contacts']
    elif base_score < 70:
        level = 'high'
        recommendations = ['Exercise caution', 'Consider alternative routes']
    else:
        level = 'critical'
        recommendations = ['Avoid area if possible', 'Contact emergency services if in danger']
    
    return {
        'level': level,
        'score': min(100, base_score),
        'factors': factors,
        'recommendations': recommendations
    }

if __name__ == '__main__':
    app.run(
        host=config.AI_HOST,
        port=config.AI_PORT,
        debug=config.DEBUG
    )