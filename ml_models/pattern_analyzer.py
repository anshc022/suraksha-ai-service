import numpy as np
from datetime import datetime, timedelta
import logging
from geopy.distance import geodesic
from collections import defaultdict
import config

logger = logging.getLogger(__name__)

class PatternAnalyzer:
    def __init__(self, db_client):
        self.db_client = db_client
    
    def analyze_patterns(self, area, time_range, incident_types=None):
        """
        Analyze incident patterns and identify hotspots in a given area
        """
        try:
            center = area['center']
            radius = area['radius_km']
            
            # Parse time range
            start_date = datetime.fromisoformat(time_range['start'].replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(time_range['end'].replace('Z', '+00:00'))
            
            # Get incidents in the area
            incidents = self.db_client.get_incidents_in_area(
                center_lat=center['lat'],
                center_lng=center['lng'],
                radius_km=radius,
                start_date=start_date,
                end_date=end_date,
                incident_types=incident_types
            )
            
            # Get panic alerts
            panic_alerts = self.db_client.get_panic_alerts_in_area(
                center_lat=center['lat'],
                center_lng=center['lng'],
                radius_km=radius,
                start_date=start_date,
                end_date=end_date
            )
            
            # Analyze patterns
            hotspots = self._identify_hotspots(incidents, panic_alerts)
            trends = self._analyze_trends(incidents, panic_alerts, start_date, end_date)
            risk_zones = self._identify_risk_zones(incidents, panic_alerts, center, radius)
            insights = self._generate_insights(incidents, panic_alerts, hotspots, trends)
            
            return {
                'hotspots': hotspots,
                'trends': trends,
                'risk_zones': risk_zones,
                'insights': insights
            }
            
        except Exception as e:
            logger.error(f"Error in pattern analysis: {str(e)}")
            return {
                'hotspots': [],
                'trends': {},
                'risk_zones': [],
                'insights': []
            }
    
    def _identify_hotspots(self, incidents, panic_alerts):
        """
        Identify incident hotspots using clustering
        """
        try:
            all_points = []
            
            # Add incident locations
            for incident in incidents:
                if 'location' in incident and 'coordinates' in incident['location']:
                    coords = incident['location']['coordinates']  # [lng, lat]
                    all_points.append({
                        'lat': coords[1],
                        'lng': coords[0],
                        'type': 'incident',
                        'subtype': incident.get('type', 'unknown'),
                        'severity': incident.get('severity', 'medium'),
                        'timestamp': incident.get('createdAt', datetime.utcnow())
                    })
            
            # Add panic alert locations
            for alert in panic_alerts:
                if 'location' in alert and 'coordinates' in alert['location']:
                    coords = alert['location']['coordinates']  # [lng, lat]
                    all_points.append({
                        'lat': coords[1],
                        'lng': coords[0],
                        'type': 'panic_alert',
                        'subtype': 'emergency',
                        'severity': 'high',
                        'timestamp': alert.get('timestamp', datetime.utcnow())
                    })
            
            if len(all_points) < config.MIN_INCIDENTS_FOR_HOTSPOT:
                return []
            
            # Simple clustering based on proximity
            hotspots = self._cluster_points(all_points, config.HOTSPOT_RADIUS)
            
            # Rank hotspots by severity and frequency
            ranked_hotspots = self._rank_hotspots(hotspots)
            
            return ranked_hotspots[:10]  # Return top 10 hotspots
            
        except Exception as e:
            logger.error(f"Error identifying hotspots: {str(e)}")
            return []
    
    def _cluster_points(self, points, radius_km):
        """
        Cluster points based on geographic proximity
        """
        clusters = []
        unclustered_points = points.copy()
        
        while unclustered_points:
            # Start new cluster with first unclustered point
            seed_point = unclustered_points.pop(0)
            cluster = {
                'center': {'lat': seed_point['lat'], 'lng': seed_point['lng']},
                'points': [seed_point],
                'incident_count': 1
            }
            
            # Find nearby points
            points_to_remove = []
            for i, point in enumerate(unclustered_points):
                distance = geodesic(
                    (seed_point['lat'], seed_point['lng']),
                    (point['lat'], point['lng'])
                ).kilometers
                
                if distance <= radius_km:
                    cluster['points'].append(point)
                    cluster['incident_count'] += 1
                    points_to_remove.append(i)
            
            # Remove clustered points
            for i in reversed(points_to_remove):
                unclustered_points.pop(i)
            
            # Update cluster center (centroid)
            if len(cluster['points']) > 1:
                avg_lat = np.mean([p['lat'] for p in cluster['points']])
                avg_lng = np.mean([p['lng'] for p in cluster['points']])
                cluster['center'] = {'lat': avg_lat, 'lng': avg_lng}
            
            # Only include clusters with minimum incidents
            if cluster['incident_count'] >= config.MIN_INCIDENTS_FOR_HOTSPOT:
                clusters.append(cluster)
        
        return clusters
    
    def _rank_hotspots(self, clusters):
        """
        Rank hotspots by risk level
        """
        ranked = []
        
        for cluster in clusters:
            # Calculate risk score
            risk_score = 0
            severity_weights = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            type_weights = {'panic_alert': 3, 'crime': 3, 'accident': 2, 'medical': 2, 'fire': 2, 'other': 1}
            
            for point in cluster['points']:
                severity_weight = severity_weights.get(point['severity'], 2)
                type_weight = type_weights.get(point['subtype'], 1)
                risk_score += severity_weight * type_weight
            
            # Normalize by time (recent incidents get higher weight)
            now = datetime.utcnow()
            time_weights = []
            for point in cluster['points']:
                if isinstance(point['timestamp'], str):
                    timestamp = datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00'))
                else:
                    timestamp = point['timestamp']
                
                days_old = (now - timestamp).days
                time_weight = max(0.1, 1.0 - (days_old / 30))  # Decay over 30 days
                time_weights.append(time_weight)
            
            avg_time_weight = np.mean(time_weights) if time_weights else 1.0
            final_score = risk_score * avg_time_weight
            
            # Get incident breakdown
            incident_breakdown = defaultdict(int)
            for point in cluster['points']:
                incident_breakdown[point['subtype']] += 1
            
            hotspot = {
                'center': cluster['center'],
                'incident_count': cluster['incident_count'],
                'risk_score': round(final_score, 2),
                'risk_level': self._get_risk_level(final_score),
                'radius_km': config.HOTSPOT_RADIUS,
                'incident_breakdown': dict(incident_breakdown),
                'most_common_type': max(incident_breakdown.items(), key=lambda x: x[1])[0],
                'recent_incidents': len([p for p in cluster['points'] 
                                       if self._is_recent(p['timestamp'], days=7)])
            }
            
            ranked.append(hotspot)
        
        # Sort by risk score (descending)
        ranked.sort(key=lambda x: x['risk_score'], reverse=True)
        
        return ranked
    
    def _analyze_trends(self, incidents, panic_alerts, start_date, end_date):
        """
        Analyze temporal trends in incident data
        """
        try:
            # Time-based analysis
            hourly_distribution = defaultdict(int)
            daily_distribution = defaultdict(int)
            weekly_distribution = defaultdict(int)
            type_distribution = defaultdict(int)
            
            all_events = []
            
            # Process incidents
            for incident in incidents:
                timestamp = incident.get('createdAt', start_date)
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                
                all_events.append({
                    'timestamp': timestamp,
                    'type': incident.get('type', 'unknown'),
                    'severity': incident.get('severity', 'medium')
                })
            
            # Process panic alerts
            for alert in panic_alerts:
                timestamp = alert.get('timestamp', start_date)
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                
                all_events.append({
                    'timestamp': timestamp,
                    'type': 'panic_alert',
                    'severity': 'high'
                })
            
            # Analyze distributions
            for event in all_events:
                ts = event['timestamp']
                
                hourly_distribution[ts.hour] += 1
                daily_distribution[ts.weekday()] += 1  # 0=Monday, 6=Sunday
                week_number = ts.isocalendar()[1]
                weekly_distribution[week_number] += 1
                type_distribution[event['type']] += 1
            
            # Calculate trends
            total_days = (end_date - start_date).days
            daily_average = len(all_events) / max(1, total_days)
            
            # Identify peak hours
            peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])[0] if hourly_distribution else 12
            peak_day = max(daily_distribution.items(), key=lambda x: x[1])[0] if daily_distribution else 0
            
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            return {
                'total_incidents': len(incidents),
                'total_panic_alerts': len(panic_alerts),
                'daily_average': round(daily_average, 2),
                'peak_hour': peak_hour,
                'peak_day': day_names[peak_day],
                'hourly_distribution': dict(hourly_distribution),
                'daily_distribution': {day_names[k]: v for k, v in daily_distribution.items()},
                'type_distribution': dict(type_distribution),
                'trend_direction': self._calculate_trend_direction(all_events, total_days)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
            return {}
    
    def _identify_risk_zones(self, incidents, panic_alerts, center, radius_km):
        """
        Identify specific risk zones within the area
        """
        try:
            # Divide area into grid cells for analysis
            grid_size = 0.005  # Roughly 500m grid cells
            risk_zones = []
            
            center_lat = center['lat']
            center_lng = center['lng']
            
            # Create grid around center point
            lat_range = radius_km / 111.0  # Rough conversion km to degrees
            lng_range = radius_km / (111.0 * np.cos(np.radians(center_lat)))
            
            for lat_offset in np.arange(-lat_range, lat_range, grid_size):
                for lng_offset in np.arange(-lng_range, lng_range, grid_size):
                    grid_lat = center_lat + lat_offset
                    grid_lng = center_lng + lng_offset
                    
                    # Count incidents in this grid cell
                    incidents_in_cell = 0
                    alerts_in_cell = 0
                    
                    for incident in incidents:
                        if 'location' in incident and 'coordinates' in incident['location']:
                            coords = incident['location']['coordinates']
                            inc_lat, inc_lng = coords[1], coords[0]
                            
                            if (abs(inc_lat - grid_lat) <= grid_size/2 and 
                                abs(inc_lng - grid_lng) <= grid_size/2):
                                incidents_in_cell += 1
                    
                    for alert in panic_alerts:
                        if 'location' in alert and 'coordinates' in alert['location']:
                            coords = alert['location']['coordinates']
                            alert_lat, alert_lng = coords[1], coords[0]
                            
                            if (abs(alert_lat - grid_lat) <= grid_size/2 and 
                                abs(alert_lng - grid_lng) <= grid_size/2):
                                alerts_in_cell += 1
                    
                    # Calculate risk for this cell
                    cell_risk = incidents_in_cell * 2 + alerts_in_cell * 3
                    
                    if cell_risk >= 3:  # Minimum threshold for risk zone
                        risk_zones.append({
                            'center': {'lat': grid_lat, 'lng': grid_lng},
                            'bounds': {
                                'north': grid_lat + grid_size/2,
                                'south': grid_lat - grid_size/2,
                                'east': grid_lng + grid_size/2,
                                'west': grid_lng - grid_size/2
                            },
                            'risk_score': cell_risk,
                            'incident_count': incidents_in_cell,
                            'alert_count': alerts_in_cell,
                            'risk_level': self._get_risk_level(cell_risk * 10)  # Scale up for level calculation
                        })
            
            # Sort by risk score and return top zones
            risk_zones.sort(key=lambda x: x['risk_score'], reverse=True)
            return risk_zones[:20]  # Top 20 risk zones
            
        except Exception as e:
            logger.error(f"Error identifying risk zones: {str(e)}")
            return []
    
    def _generate_insights(self, incidents, panic_alerts, hotspots, trends):
        """
        Generate actionable insights from the analysis
        """
        insights = []
        
        try:
            total_incidents = len(incidents) + len(panic_alerts)
            
            # Hotspot insights
            if hotspots:
                top_hotspot = hotspots[0]
                insights.append({
                    'type': 'hotspot',
                    'severity': 'high',
                    'message': f"Critical hotspot identified with {top_hotspot['incident_count']} incidents. "
                              f"Primary incident type: {top_hotspot['most_common_type']}",
                    'recommendation': 'Increase patrol frequency and consider safety infrastructure improvements.'
                })
            
            # Trend insights
            if trends and total_incidents > 0:
                if 'peak_hour' in trends:
                    peak_hour = trends['peak_hour']
                    if 22 <= peak_hour or peak_hour <= 5:  # Night hours
                        insights.append({
                            'type': 'temporal',
                            'severity': 'medium',
                            'message': f"Peak incident time is {peak_hour}:00 (night hours)",
                            'recommendation': 'Enhance night-time security measures and lighting.'
                        })
                
                if 'trend_direction' in trends:
                    direction = trends['trend_direction']
                    if direction == 'increasing':
                        insights.append({
                            'type': 'trend',
                            'severity': 'high',
                            'message': 'Incident trend is increasing over the analyzed period',
                            'recommendation': 'Immediate intervention and additional safety measures required.'
                        })
            
            # Type-specific insights
            if trends and 'type_distribution' in trends:
                most_common = max(trends['type_distribution'].items(), key=lambda x: x[1])
                if most_common[1] >= total_incidents * 0.4:  # 40% or more
                    insights.append({
                        'type': 'incident_pattern',
                        'severity': 'medium',
                        'message': f"{most_common[0]} incidents are predominant ({most_common[1]} out of {total_incidents})",
                        'recommendation': f'Implement targeted prevention strategies for {most_common[0]} incidents.'
                    })
            
            # Safety recommendations
            if total_incidents > 20:  # High incident area
                insights.append({
                    'type': 'safety',
                    'severity': 'high',
                    'message': f'High incident density detected ({total_incidents} incidents in analyzed period)',
                    'recommendation': 'Consider this area as high-risk and advise increased caution for travelers.'
                })
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return []
    
    def _calculate_trend_direction(self, events, total_days):
        """
        Calculate whether incidents are increasing, decreasing, or stable
        """
        if len(events) < 4 or total_days < 7:
            return 'insufficient_data'
        
        # Split period into two halves
        sorted_events = sorted(events, key=lambda x: x['timestamp'])
        mid_point = len(sorted_events) // 2
        
        first_half = sorted_events[:mid_point]
        second_half = sorted_events[mid_point:]
        
        first_half_rate = len(first_half) / (total_days / 2)
        second_half_rate = len(second_half) / (total_days / 2)
        
        change_ratio = second_half_rate / first_half_rate if first_half_rate > 0 else 1
        
        if change_ratio > 1.2:
            return 'increasing'
        elif change_ratio < 0.8:
            return 'decreasing'
        else:
            return 'stable'
    
    def _get_risk_level(self, score):
        """Convert numeric risk score to categorical level"""
        if score < 10:
            return 'low'
        elif score < 20:
            return 'moderate'
        elif score < 35:
            return 'high'
        else:
            return 'critical'
    
    def _is_recent(self, timestamp, days=7):
        """Check if timestamp is within recent days"""
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        return timestamp >= cutoff