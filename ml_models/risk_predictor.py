import numpy as np
from datetime import datetime, timedelta
import logging
from geopy.distance import geodesic
import config

logger = logging.getLogger(__name__)

class RiskPredictor:
    def __init__(self, db_client):
        self.db_client = db_client
        self.model = None
        self.risk_cache = {}  # Simple cache for performance
    
    def predict_route_risk(self, route, time_of_day='day', user_id=None):
        """
        Predict risk score for a given route based on historical data
        Returns a score from 0-100 (higher = more risky)
        """
        try:
            start_point = route['start']
            end_point = route['end']
            waypoints = route.get('waypoints', [])
            
            # Calculate base risk from historical incidents
            base_risk = self._calculate_historical_risk(start_point, end_point, waypoints)
            
            # Apply time-based modifiers
            time_modifier = self._get_time_risk_modifier(time_of_day)
            
            # Apply route characteristics modifier
            route_modifier = self._get_route_characteristics_modifier(route)
            
            # Calculate final risk score
            risk_score = min(100, base_risk * time_modifier * route_modifier)
            
            # Store prediction for future model training
            self._store_prediction({
                'route': route,
                'time_of_day': time_of_day,
                'user_id': user_id,
                'risk_score': risk_score,
                'components': {
                    'base_risk': base_risk,
                    'time_modifier': time_modifier,
                    'route_modifier': route_modifier
                }
            })
            
            return round(risk_score, 2)
            
        except Exception as e:
            logger.error(f"Error in risk prediction: {str(e)}")
            return 30.0  # Default moderate risk
    
    def _calculate_historical_risk(self, start_point, end_point, waypoints):
        """
        Calculate risk based on historical incident data
        """
        try:
            all_points = [start_point] + waypoints + [end_point]
            total_risk = 0
            point_count = 0
            
            for point in all_points:
                # Get incidents within radius of this point
                incidents = self.db_client.get_incidents_in_area(
                    center_lat=point['lat'],
                    center_lng=point['lng'],
                    radius_km=config.RISK_PREDICTION_RADIUS,
                    start_date=datetime.utcnow() - timedelta(days=365)  # Last year
                )
                
                # Get panic alerts
                panic_alerts = self.db_client.get_panic_alerts_in_area(
                    center_lat=point['lat'],
                    center_lng=point['lng'],
                    radius_km=config.RISK_PREDICTION_RADIUS,
                    start_date=datetime.utcnow() - timedelta(days=365)
                )
                
                # Calculate risk for this point
                point_risk = self._calculate_point_risk(incidents, panic_alerts)
                total_risk += point_risk
                point_count += 1
            
            # Average risk across all points
            avg_risk = total_risk / point_count if point_count > 0 else 20
            
            return min(80, avg_risk)  # Cap base risk at 80
            
        except Exception as e:
            logger.error(f"Error calculating historical risk: {str(e)}")
            return 20.0  # Default base risk
    
    def _calculate_point_risk(self, incidents, panic_alerts):
        """
        Calculate risk score for a specific point based on incident density
        """
        try:
            # Weight different incident types
            incident_weights = {
                'crime': 3.0,
                'accident': 2.0,
                'medical': 1.5,
                'fire': 2.5,
                'other': 1.0
            }
            
            # Calculate weighted incident score
            incident_score = 0
            for incident in incidents:
                incident_type = incident.get('type', 'other')
                severity = incident.get('severity', 'medium')
                
                weight = incident_weights.get(incident_type, 1.0)
                
                # Severity multiplier
                severity_multiplier = {
                    'low': 0.5,
                    'medium': 1.0,
                    'high': 1.5,
                    'critical': 2.0
                }.get(severity, 1.0)
                
                incident_score += weight * severity_multiplier
            
            # Add panic alert score (each alert adds fixed risk)
            panic_score = len(panic_alerts) * 2.0
            
            # Combine scores with decay factor for time
            total_score = incident_score + panic_score
            
            # Convert to 0-100 scale
            # Assuming 10+ incidents in area represents high risk (80+ score)
            normalized_score = min(80, (total_score / 10) * 80)
            
            return max(5, normalized_score)  # Minimum baseline risk
            
        except Exception as e:
            logger.error(f"Error calculating point risk: {str(e)}")
            return 20.0
    
    def _get_time_risk_modifier(self, time_of_day):
        """
        Get risk modifier based on time of day
        """
        time_modifiers = {
            'morning': 0.8,      # Lower risk during morning
            'afternoon': 0.9,    # Lower risk during afternoon
            'evening': 1.1,      # Slightly higher risk in evening
            'night': 1.3,        # Higher risk at night
            'late_night': 1.5    # Highest risk late at night
        }
        
        return time_modifiers.get(time_of_day, 1.0)
    
    def _get_route_characteristics_modifier(self, route):
        """
        Get risk modifier based on route characteristics
        """
        try:
            start = route['start']
            end = route['end']
            
            # Calculate route distance
            distance = geodesic(
                (start['lat'], start['lng']),
                (end['lat'], end['lng'])
            ).kilometers
            
            # Distance modifier (longer routes have slightly higher risk)
            distance_modifier = 1.0 + (distance / 100) * 0.1  # +10% per 100km
            
            # Number of waypoints (more stops = more exposure)
            waypoint_count = len(route.get('waypoints', []))
            waypoint_modifier = 1.0 + (waypoint_count * 0.05)  # +5% per waypoint
            
            return min(1.5, distance_modifier * waypoint_modifier)  # Cap at 1.5x
            
        except Exception as e:
            logger.error(f"Error calculating route characteristics: {str(e)}")
            return 1.0
    
    def _store_prediction(self, prediction_data):
        """
        Store prediction for future model improvement
        """
        try:
            self.db_client.store_risk_prediction(prediction_data)
        except Exception as e:
            logger.error(f"Error storing prediction: {str(e)}")
    
    def get_area_risk_summary(self, center_lat, center_lng, radius_km=5.0):
        """
        Get risk summary for a specific area
        """
        try:
            # Get recent incidents
            incidents = self.db_client.get_incidents_in_area(
                center_lat=center_lat,
                center_lng=center_lng,
                radius_km=radius_km,
                start_date=datetime.utcnow() - timedelta(days=30)
            )
            
            panic_alerts = self.db_client.get_panic_alerts_in_area(
                center_lat=center_lat,
                center_lng=center_lng,
                radius_km=radius_km,
                start_date=datetime.utcnow() - timedelta(days=30)
            )
            
            # Calculate area risk
            area_risk = self._calculate_point_risk(incidents, panic_alerts)
            
            # Incident breakdown
            incident_breakdown = {}
            for incident in incidents:
                incident_type = incident.get('type', 'other')
                incident_breakdown[incident_type] = incident_breakdown.get(incident_type, 0) + 1
            
            return {
                'risk_score': round(area_risk, 2),
                'risk_level': self._get_risk_level(area_risk),
                'total_incidents': len(incidents),
                'total_panic_alerts': len(panic_alerts),
                'incident_breakdown': incident_breakdown,
                'time_period': '30 days'
            }
            
        except Exception as e:
            logger.error(f"Error getting area risk summary: {str(e)}")
            return {
                'risk_score': 25.0,
                'risk_level': 'moderate',
                'total_incidents': 0,
                'total_panic_alerts': 0,
                'incident_breakdown': {},
                'time_period': '30 days'
            }
    
    def _get_risk_level(self, score):
        """Convert numeric risk score to categorical level"""
        if score < 25:
            return 'low'
        elif score < 50:
            return 'moderate'
        elif score < 75:
            return 'high'
        else:
            return 'critical'