import numpy as np
from datetime import datetime, timedelta
import logging
from geopy.distance import geodesic
import config
from scipy import stats

logger = logging.getLogger(__name__)

class AnomalyDetector:
    def __init__(self, db_client):
        self.db_client = db_client
        self.user_profiles = {}  # Cache for user movement profiles
    
    def detect_anomalies(self, user_id, location_data):
        """
        Detect anomalies in user movement patterns
        Returns anomaly information with confidence score
        """
        try:
            if len(location_data) < 2:
                return {
                    'is_anomaly': False,
                    'confidence': 0.0,
                    'type': None,
                    'details': 'Insufficient data'
                }
            
            # Prepare location data
            processed_data = self._process_location_data(location_data)
            
            # Get user's historical movement profile
            user_profile = self._get_user_movement_profile(user_id)
            
            # Run multiple anomaly detection algorithms
            speed_anomaly = self._detect_speed_anomaly(processed_data, user_profile)
            pattern_anomaly = self._detect_pattern_anomaly(processed_data, user_profile)
            location_anomaly = self._detect_location_anomaly(processed_data, user_profile)
            time_anomaly = self._detect_time_anomaly(processed_data, user_profile)
            
            # Combine results
            anomalies = [speed_anomaly, pattern_anomaly, location_anomaly, time_anomaly]
            max_confidence_anomaly = max(anomalies, key=lambda x: x['confidence'])
            
            # Store result for future learning
            self._store_anomaly_result(user_id, location_data, max_confidence_anomaly)
            
            return max_confidence_anomaly
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {str(e)}")
            return {
                'is_anomaly': False,
                'confidence': 0.0,
                'type': 'error',
                'details': f'Detection error: {str(e)}'
            }
    
    def _process_location_data(self, location_data):
        """
        Process and enrich location data with derived features
        """
        processed = []
        
        for i, point in enumerate(location_data):
            processed_point = {
                'lat': point['lat'],
                'lng': point['lng'],
                'timestamp': datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00')),
                'accuracy': point.get('accuracy', 10),
                'speed': point.get('speed', 0)
            }
            
            # Calculate derived features
            if i > 0:
                prev_point = processed[i-1]
                
                # Distance traveled
                distance = geodesic(
                    (prev_point['lat'], prev_point['lng']),
                    (processed_point['lat'], processed_point['lng'])
                ).meters
                
                # Time difference
                time_diff = (processed_point['timestamp'] - prev_point['timestamp']).total_seconds()
                
                # Calculated speed (if not provided)
                if processed_point['speed'] == 0 and time_diff > 0:
                    calculated_speed = (distance / time_diff) * 3.6  # m/s to km/h
                    processed_point['calculated_speed'] = calculated_speed
                else:
                    processed_point['calculated_speed'] = processed_point['speed']
                
                processed_point['distance_from_prev'] = distance
                processed_point['time_from_prev'] = time_diff
            else:
                processed_point['calculated_speed'] = 0
                processed_point['distance_from_prev'] = 0
                processed_point['time_from_prev'] = 0
            
            processed.append(processed_point)
        
        return processed
    
    def _get_user_movement_profile(self, user_id):
        """
        Get or build user's historical movement profile
        """
        if user_id in self.user_profiles:
            return self.user_profiles[user_id]
        
        try:
            # Get user's location history
            history = self.db_client.get_user_location_history(user_id, hours_back=24*7)  # Last week
            
            if len(history) < 10:
                # Not enough history, use default profile
                profile = self._get_default_profile()
            else:
                profile = self._build_user_profile(history)
            
            # Cache the profile
            self.user_profiles[user_id] = profile
            
            return profile
            
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return self._get_default_profile()
    
    def _build_user_profile(self, location_history):
        """
        Build movement profile from historical data
        """
        speeds = []
        distances = []
        time_intervals = []
        locations = []
        
        for i in range(1, len(location_history)):
            curr = location_history[i]
            prev = location_history[i-1]
            
            # Calculate movement metrics
            if 'coordinates' in curr['location'] and 'coordinates' in prev['location']:
                curr_coords = curr['location']['coordinates']  # [lng, lat]
                prev_coords = prev['location']['coordinates']
                
                distance = geodesic(
                    (prev_coords[1], prev_coords[0]),
                    (curr_coords[1], curr_coords[0])
                ).meters
                
                time_diff = (curr['timestamp'] - prev['timestamp']).total_seconds()
                
                if time_diff > 0:
                    speed = (distance / time_diff) * 3.6  # km/h
                    
                    speeds.append(speed)
                    distances.append(distance)
                    time_intervals.append(time_diff)
                    locations.append((curr_coords[1], curr_coords[0]))  # lat, lng
        
        # Calculate statistical profile
        profile = {
            'avg_speed': np.mean(speeds) if speeds else 0,
            'max_speed': np.max(speeds) if speeds else 0,
            'speed_std': np.std(speeds) if speeds else 0,
            'avg_distance': np.mean(distances) if distances else 0,
            'avg_time_interval': np.mean(time_intervals) if time_intervals else 0,
            'typical_locations': self._get_frequent_locations(locations),
            'speed_percentiles': {
                '95': np.percentile(speeds, 95) if speeds else 0,
                '99': np.percentile(speeds, 99) if speeds else 0
            }
        }
        
        return profile
    
    def _get_default_profile(self):
        """
        Default movement profile for new users
        """
        return {
            'avg_speed': 25.0,  # km/h
            'max_speed': 60.0,
            'speed_std': 15.0,
            'avg_distance': 500.0,  # meters
            'avg_time_interval': 300.0,  # seconds
            'typical_locations': [],
            'speed_percentiles': {
                '95': 80.0,
                '99': 120.0
            }
        }
    
    def _get_frequent_locations(self, locations, radius_m=100):
        """
        Find frequently visited locations
        """
        if len(locations) < 5:
            return []
        
        # Simple clustering based on proximity
        clusters = []
        for location in locations:
            added_to_cluster = False
            
            for cluster in clusters:
                # Check if location is close to cluster center
                cluster_center = cluster['center']
                distance = geodesic(location, cluster_center).meters
                
                if distance <= radius_m:
                    cluster['points'].append(location)
                    cluster['count'] += 1
                    added_to_cluster = True
                    break
            
            if not added_to_cluster:
                clusters.append({
                    'center': location,
                    'points': [location],
                    'count': 1
                })
        
        # Return clusters with at least 3 visits
        frequent_locations = []
        for cluster in clusters:
            if cluster['count'] >= 3:
                frequent_locations.append({
                    'center': cluster['center'],
                    'visit_count': cluster['count']
                })
        
        return frequent_locations
    
    def _detect_speed_anomaly(self, processed_data, user_profile):
        """
        Detect speed-based anomalies
        """
        try:
            speeds = [point['calculated_speed'] for point in processed_data if point['calculated_speed'] > 0]
            
            if not speeds:
                return {'is_anomaly': False, 'confidence': 0.0, 'type': None}
            
            max_speed = max(speeds)
            avg_speed = np.mean(speeds)
            
            # Check against absolute thresholds
            if max_speed > config.MOVEMENT_SPEED_THRESHOLD:
                return {
                    'is_anomaly': True,
                    'confidence': 0.9,
                    'type': 'excessive_speed',
                    'details': f'Speed {max_speed:.1f} km/h exceeds threshold'
                }
            
            # Check against user's typical speed profile
            user_95th = user_profile['speed_percentiles']['95']
            user_99th = user_profile['speed_percentiles']['99']
            
            if max_speed > user_99th * 1.5:  # 50% above 99th percentile
                return {
                    'is_anomaly': True,
                    'confidence': 0.8,
                    'type': 'unusual_speed',
                    'details': f'Speed {max_speed:.1f} km/h is unusual for this user'
                }
            
            # Check for sudden speed changes
            speed_changes = []
            for i in range(1, len(speeds)):
                change = abs(speeds[i] - speeds[i-1])
                speed_changes.append(change)
            
            if speed_changes and max(speed_changes) > 50:  # Sudden 50+ km/h change
                return {
                    'is_anomaly': True,
                    'confidence': 0.7,
                    'type': 'sudden_speed_change',
                    'details': f'Sudden speed change detected: {max(speed_changes):.1f} km/h'
                }
            
            return {'is_anomaly': False, 'confidence': 0.0, 'type': None}
            
        except Exception as e:
            logger.error(f"Error in speed anomaly detection: {str(e)}")
            return {'is_anomaly': False, 'confidence': 0.0, 'type': 'error'}
    
    def _detect_pattern_anomaly(self, processed_data, user_profile):
        """
        Detect pattern-based anomalies
        """
        try:
            if len(processed_data) < 3:
                return {'is_anomaly': False, 'confidence': 0.0, 'type': None}
            
            # Check for erratic movement patterns
            directions = []
            for i in range(1, len(processed_data)):
                curr = processed_data[i]
                prev = processed_data[i-1]
                
                # Calculate bearing change
                if curr['distance_from_prev'] > 10:  # Only for meaningful movements
                    lat_diff = curr['lat'] - prev['lat']
                    lng_diff = curr['lng'] - prev['lng']
                    bearing = np.arctan2(lng_diff, lat_diff)
                    directions.append(bearing)
            
            if len(directions) >= 3:
                # Check for excessive direction changes
                direction_changes = []
                for i in range(1, len(directions)):
                    change = abs(directions[i] - directions[i-1])
                    # Normalize to 0-π
                    if change > np.pi:
                        change = 2*np.pi - change
                    direction_changes.append(change)
                
                # If most direction changes are > 90 degrees, it's erratic
                large_changes = sum(1 for change in direction_changes if change > np.pi/2)
                erratic_ratio = large_changes / len(direction_changes)
                
                if erratic_ratio > 0.7:  # 70% of movements are erratic
                    return {
                        'is_anomaly': True,
                        'confidence': 0.6,
                        'type': 'erratic_movement',
                        'details': f'Erratic movement pattern detected ({erratic_ratio:.1%} erratic changes)'
                    }
            
            return {'is_anomaly': False, 'confidence': 0.0, 'type': None}
            
        except Exception as e:
            logger.error(f"Error in pattern anomaly detection: {str(e)}")
            return {'is_anomaly': False, 'confidence': 0.0, 'type': 'error'}
    
    def _detect_location_anomaly(self, processed_data, user_profile):
        """
        Detect location-based anomalies
        """
        try:
            if not user_profile['typical_locations']:
                return {'is_anomaly': False, 'confidence': 0.0, 'type': None}
            
            # Check if current locations are far from typical locations
            current_locations = [(point['lat'], point['lng']) for point in processed_data]
            
            min_distances = []
            for curr_loc in current_locations:
                distances_to_typical = []
                for typical_loc in user_profile['typical_locations']:
                    distance = geodesic(curr_loc, typical_loc['center']).kilometers
                    distances_to_typical.append(distance)
                
                if distances_to_typical:
                    min_distances.append(min(distances_to_typical))
            
            if min_distances:
                avg_distance_from_typical = np.mean(min_distances)
                
                # If average distance > 10km from typical locations
                if avg_distance_from_typical > 10.0:
                    return {
                        'is_anomaly': True,
                        'confidence': 0.5,
                        'type': 'unusual_location',
                        'details': f'Location {avg_distance_from_typical:.1f}km from typical areas'
                    }
            
            return {'is_anomaly': False, 'confidence': 0.0, 'type': None}
            
        except Exception as e:
            logger.error(f"Error in location anomaly detection: {str(e)}")
            return {'is_anomaly': False, 'confidence': 0.0, 'type': 'error'}
    
    def _detect_time_anomaly(self, processed_data, user_profile):
        """
        Detect time-based anomalies
        """
        try:
            # Check for unusual timing (very late night movement for non-night users)
            current_hour = processed_data[0]['timestamp'].hour
            
            # Simple heuristic: movement between 2 AM and 5 AM is unusual
            if 2 <= current_hour <= 5:
                return {
                    'is_anomaly': True,
                    'confidence': 0.4,
                    'type': 'unusual_time',
                    'details': f'Movement detected at {current_hour}:00 (late night)'
                }
            
            return {'is_anomaly': False, 'confidence': 0.0, 'type': None}
            
        except Exception as e:
            logger.error(f"Error in time anomaly detection: {str(e)}")
            return {'is_anomaly': False, 'confidence': 0.0, 'type': 'error'}
    
    def _store_anomaly_result(self, user_id, location_data, anomaly_result):
        """
        Store anomaly detection result for future learning
        """
        try:
            anomaly_data = {
                'user_id': user_id,
                'location_data_sample': location_data[:5],  # Store sample
                'anomaly_result': anomaly_result,
                'detection_timestamp': datetime.utcnow()
            }
            
            self.db_client.store_anomaly_detection(anomaly_data)
            
        except Exception as e:
            logger.error(f"Error storing anomaly result: {str(e)}")