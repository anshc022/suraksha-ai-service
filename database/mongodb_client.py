from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import logging
import config
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MongoDBClient:
    def __init__(self):
        self.client = None
        self.db = None
        self.connect()
    
    def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(config.MONGODB_URL)
            self.db = self.client[config.MONGODB_DATABASE]
            # Test connection
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    def get_incidents_in_area(self, center_lat, center_lng, radius_km, start_date=None, end_date=None, incident_types=None):
        """
        Get incidents within a specified area and time range
        """
        try:
            # Build query
            query = {
                'location': {
                    '$geoWithin': {
                        '$centerSphere': [
                            [center_lng, center_lat],
                            radius_km / 6371  # Convert km to radians
                        ]
                    }
                }
            }
            
            # Add date range filter
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter['$gte'] = start_date
                if end_date:
                    date_filter['$lte'] = end_date
                query['createdAt'] = date_filter
            
            # Add incident type filter
            if incident_types:
                query['type'] = {'$in': incident_types}
            
            # Execute query - using 'incidents' collection (lowercase, pluralized by Mongoose)
            incidents = list(self.db.incidents.find(query))
            return incidents
            
        except Exception as e:
            logger.error(f"Error fetching incidents: {str(e)}")
            return []
    
    def get_user_location_history(self, user_id, hours_back=24):
        """
        Get user's recent location history
        """
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            query = {
                'userId': user_id,
                'timestamp': {'$gte': start_time}
            }
            
            # Using 'userlocations' collection (lowercase, pluralized by Mongoose)
            locations = list(self.db.userlocations.find(query).sort('timestamp', 1))
            return locations
            
        except Exception as e:
            logger.error(f"Error fetching user location history: {str(e)}")
            return []
    
    def get_panic_alerts_in_area(self, center_lat, center_lng, radius_km, start_date=None, end_date=None):
        """
        Get panic alerts within a specified area and time range
        """
        try:
            query = {
                'location': {
                    '$geoWithin': {
                        '$centerSphere': [
                            [center_lng, center_lat],
                            radius_km / 6371
                        ]
                    }
                }
            }
            
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter['$gte'] = start_date
                if end_date:
                    date_filter['$lte'] = end_date
                query['timestamp'] = date_filter
            
            # Using 'panicalerts' collection (lowercase, pluralized by Mongoose)
            alerts = list(self.db.panicalerts.find(query))
            return alerts
            
        except Exception as e:
            logger.error(f"Error fetching panic alerts: {str(e)}")
            return []
    
    def get_historical_route_data(self, start_lat, start_lng, end_lat, end_lng, radius_km=1.0):
        """
        Get historical incident data along a route
        """
        try:
            # For MVP, we'll check incidents near start and end points
            # In production, this would analyze the entire route corridor
            
            start_incidents = self.get_incidents_in_area(start_lat, start_lng, radius_km)
            end_incidents = self.get_incidents_in_area(end_lat, end_lng, radius_km)
            
            # Combine and deduplicate
            all_incidents = start_incidents + end_incidents
            unique_incidents = []
            seen_ids = set()
            
            for incident in all_incidents:
                incident_id = str(incident.get('_id'))
                if incident_id not in seen_ids:
                    unique_incidents.append(incident)
                    seen_ids.add(incident_id)
            
            return unique_incidents
            
        except Exception as e:
            logger.error(f"Error fetching route data: {str(e)}")
            return []
    
    def store_risk_prediction(self, prediction_data):
        """
        Store risk prediction for future analysis
        """
        try:
            prediction_data['timestamp'] = datetime.utcnow()
            result = self.db.risk_predictions.insert_one(prediction_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing risk prediction: {str(e)}")
            return None
    
    def store_anomaly_detection(self, anomaly_data):
        """
        Store anomaly detection result
        """
        try:
            anomaly_data['timestamp'] = datetime.utcnow()
            result = self.db.anomaly_detections.insert_one(anomaly_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing anomaly detection: {str(e)}")
            return None
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")