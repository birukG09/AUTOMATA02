"""
Anomaly Detection Module for AUTOMATA02.
Applies ML models to detect unusual patterns in aggregated data.
"""

import json
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import warnings
from utils.logger import setup_logger

# Suppress sklearn warnings
warnings.filterwarnings('ignore', category=UserWarning)

logger = setup_logger()

class Anomaly:
    """Represents a detected anomaly"""
    
    def __init__(self, anomaly_id: str, anomaly_type: str, severity: str,
                 description: str, data_points: Dict[str, Any],
                 confidence: float, detected_at: datetime):
        self.anomaly_id = anomaly_id
        self.anomaly_type = anomaly_type  # 'volume', 'pattern', 'outlier', 'trend'
        self.severity = severity  # 'low', 'medium', 'high', 'critical'
        self.description = description
        self.data_points = data_points
        self.confidence = confidence
        self.detected_at = detected_at
        self.status = 'active'  # 'active', 'resolved', 'dismissed'

class AnomalyDetector:
    """Main anomaly detection engine"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        
        # Initialize anomaly database
        self._init_anomaly_db()
        
        # Detection models
        self.models = {
            'isolation_forest': IsolationForest(contamination=0.1, random_state=42),
            'dbscan': DBSCAN(eps=0.5, min_samples=3)
        }
        
        # Scalers for normalization
        self.scalers = {
            'standard': StandardScaler()
        }
        
        # Anomaly thresholds
        self.thresholds = {
            'volume_change': 0.4,      # 40% change in volume
            'pattern_deviation': 0.3,   # 30% deviation from pattern
            'outlier_threshold': 2.5,   # 2.5 standard deviations
            'trend_change': 0.5         # 50% trend change
        }
        
        # Recent data cache
        self.data_cache = {}
        self.cache_expiry = timedelta(hours=1)
    
    def _init_anomaly_db(self):
        """Initialize anomaly detection database tables"""
        try:
            anomaly_db_path = Path.home() / ".automata02" / "anomalies.sqlite"
            
            with sqlite3.connect(str(anomaly_db_path)) as conn:
                cursor = conn.cursor()
                
                # Anomalies table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS anomalies (
                        anomaly_id TEXT PRIMARY KEY,
                        anomaly_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        description TEXT NOT NULL,
                        data_points TEXT,
                        confidence REAL,
                        detected_at TEXT,
                        status TEXT DEFAULT 'active',
                        resolved_at TEXT,
                        resolution_notes TEXT
                    )
                ''')
                
                # Detection metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS detection_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_type TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        value REAL NOT NULL,
                        baseline REAL,
                        threshold REAL,
                        timestamp TEXT NOT NULL,
                        is_anomalous BOOLEAN DEFAULT 0
                    )
                ''')
                
                # Baseline patterns table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS baseline_patterns (
                        pattern_id TEXT PRIMARY KEY,
                        pattern_type TEXT NOT NULL,
                        pattern_data TEXT NOT NULL,
                        created_at TEXT,
                        last_updated TEXT,
                        sample_count INTEGER DEFAULT 0
                    )
                ''')
                
                conn.commit()
                logger.info("Anomaly detection database initialized")
                
        except Exception as e:
            logger.error(f"Error initializing anomaly database: {e}")
    
    def run_anomaly_detection(self) -> List[Anomaly]:
        """Run comprehensive anomaly detection"""
        anomalies = []
        
        try:
            # Detect different types of anomalies
            anomalies.extend(self._detect_volume_anomalies())
            anomalies.extend(self._detect_pattern_anomalies())
            anomalies.extend(self._detect_file_size_outliers())
            anomalies.extend(self._detect_activity_trend_changes())
            anomalies.extend(self._detect_classification_anomalies())
            
            # Save detected anomalies
            for anomaly in anomalies:
                self._save_anomaly(anomaly)
            
            logger.info(f"Detected {len(anomalies)} anomalies")
            return anomalies
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return []
    
    def _detect_volume_anomalies(self) -> List[Anomaly]:
        """Detect anomalies in file processing volume"""
        anomalies = []
        
        try:
            # Get recent file activity
            recent_data = self._get_recent_file_activity(days=30)
            if len(recent_data) < 7:  # Need at least a week of data
                return anomalies
            
            df = pd.DataFrame(recent_data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Calculate daily volumes
            daily_volumes = df.groupby('date')['count'].sum()
            
            # Calculate baseline (mean of last 3 weeks, excluding last 3 days)
            baseline_period = daily_volumes[:-3]  # Exclude last 3 days
            if len(baseline_period) < 7:
                return anomalies
            
            baseline_mean = baseline_period.mean()
            baseline_std = baseline_period.std()
            
            # Check recent days for anomalies
            recent_days = daily_volumes[-3:]  # Last 3 days
            
            for date, volume in recent_days.items():
                # Calculate z-score
                if baseline_std > 0:
                    z_score = (volume - baseline_mean) / baseline_std
                else:
                    z_score = 0
                
                # Check for significant deviations
                if abs(z_score) > self.thresholds['outlier_threshold']:
                    severity = self._calculate_severity(abs(z_score), 2.0, 3.0, 4.0)
                    
                    if volume > baseline_mean:
                        description = f"⚠️ Unusual spike in file activity: {volume:.0f} files processed on {date.strftime('%Y-%m-%d')} (baseline: {baseline_mean:.0f})"
                    else:
                        description = f"⚠️ Unusual drop in file activity: {volume:.0f} files processed on {date.strftime('%Y-%m-%d')} (baseline: {baseline_mean:.0f})"
                    
                    anomaly = Anomaly(
                        anomaly_id=f"volume_{date.strftime('%Y%m%d')}",
                        anomaly_type='volume',
                        severity=severity,
                        description=description,
                        data_points={
                            'date': date.isoformat(),
                            'volume': volume,
                            'baseline': baseline_mean,
                            'z_score': z_score,
                            'change_percent': ((volume - baseline_mean) / baseline_mean) * 100
                        },
                        confidence=min(0.95, abs(z_score) / 5.0),
                        detected_at=datetime.now()
                    )
                    anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting volume anomalies: {e}")
            return []
    
    def _detect_pattern_anomalies(self) -> List[Anomaly]:
        """Detect anomalies in file processing patterns"""
        anomalies = []
        
        try:
            # Get file type distribution for recent vs historical data
            recent_distribution = self._get_file_type_distribution(days=7)
            historical_distribution = self._get_file_type_distribution(days=30, exclude_recent=7)
            
            if not recent_distribution or not historical_distribution:
                return anomalies
            
            # Compare distributions
            all_types = set(recent_distribution.keys()) | set(historical_distribution.keys())
            
            for file_type in all_types:
                recent_count = recent_distribution.get(file_type, 0)
                historical_avg = historical_distribution.get(file_type, 0) / 3  # 3 weeks average
                
                if historical_avg > 0:
                    change_ratio = recent_count / historical_avg
                    
                    # Detect significant changes
                    if change_ratio > 2.0 or change_ratio < 0.5:
                        severity = self._calculate_severity_from_ratio(change_ratio)
                        
                        if change_ratio > 2.0:
                            description = f"⚠️ Unusual increase in {file_type} files: {recent_count} this week vs {historical_avg:.1f} average"
                        else:
                            description = f"⚠️ Unusual decrease in {file_type} files: {recent_count} this week vs {historical_avg:.1f} average"
                        
                        anomaly = Anomaly(
                            anomaly_id=f"pattern_{file_type}_{datetime.now().strftime('%Y%m%d')}",
                            anomaly_type='pattern',
                            severity=severity,
                            description=description,
                            data_points={
                                'file_type': file_type,
                                'recent_count': recent_count,
                                'historical_average': historical_avg,
                                'change_ratio': change_ratio,
                                'change_percent': ((recent_count - historical_avg) / historical_avg) * 100
                            },
                            confidence=min(0.9, abs(change_ratio - 1.0) / 2.0),
                            detected_at=datetime.now()
                        )
                        anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting pattern anomalies: {e}")
            return []
    
    def _detect_file_size_outliers(self) -> List[Anomaly]:
        """Detect outliers in file sizes"""
        anomalies = []
        
        try:
            # Get recent file sizes
            recent_files = self.db_manager.search_files(limit=1000)
            if len(recent_files) < 50:  # Need sufficient data
                return anomalies
            
            # Extract file sizes
            sizes = [f['size_bytes'] for f in recent_files if f.get('size_bytes', 0) > 0]
            if len(sizes) < 50:
                return anomalies
            
            sizes = np.array(sizes)
            
            # Use Isolation Forest to detect outliers
            if len(sizes) > 100:
                sizes_reshaped = sizes.reshape(-1, 1)
                
                # Fit model
                model = IsolationForest(contamination=0.05, random_state=42)
                outliers = model.fit_predict(sizes_reshaped)
                
                # Find outlier files
                outlier_indices = np.where(outliers == -1)[0]
                
                for idx in outlier_indices:
                    file_info = recent_files[idx]
                    size = sizes[idx]
                    
                    # Calculate how extreme this outlier is
                    percentile = (np.sum(sizes < size) / len(sizes)) * 100
                    
                    if percentile > 99.5 or percentile < 0.5:
                        severity = 'high' if percentile > 99.9 or percentile < 0.1 else 'medium'
                        
                        if percentile > 99.5:
                            description = f"⚠️ Unusually large file detected: {Path(file_info['path']).name} ({self._format_file_size(size)})"
                        else:
                            description = f"⚠️ Unusually small file detected: {Path(file_info['path']).name} ({self._format_file_size(size)})"
                        
                        anomaly = Anomaly(
                            anomaly_id=f"size_outlier_{file_info['id']}",
                            anomaly_type='outlier',
                            severity=severity,
                            description=description,
                            data_points={
                                'file_path': file_info['path'],
                                'size_bytes': size,
                                'size_formatted': self._format_file_size(size),
                                'percentile': percentile,
                                'median_size': np.median(sizes),
                                'mean_size': np.mean(sizes)
                            },
                            confidence=0.8,
                            detected_at=datetime.now()
                        )
                        anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting file size outliers: {e}")
            return []
    
    def _detect_activity_trend_changes(self) -> List[Anomaly]:
        """Detect changes in activity trends"""
        anomalies = []
        
        try:
            # Get hourly activity for the last week
            hourly_data = self._get_hourly_activity(days=14)
            if len(hourly_data) < 100:  # Need sufficient data points
                return anomalies
            
            df = pd.DataFrame(hourly_data)
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.sort_values('datetime')
            
            # Split into two weeks for comparison
            mid_point = len(df) // 2
            week1 = df.iloc[:mid_point]
            week2 = df.iloc[mid_point:]
            
            # Compare hourly patterns
            week1_hourly = week1.groupby(week1['datetime'].dt.hour)['count'].mean()
            week2_hourly = week2.groupby(week2['datetime'].dt.hour)['count'].mean()
            
            # Find significant changes
            for hour in range(24):
                w1_avg = week1_hourly.get(hour, 0)
                w2_avg = week2_hourly.get(hour, 0)
                
                if w1_avg > 0:
                    change_ratio = w2_avg / w1_avg
                    
                    if change_ratio > 3.0 or change_ratio < 0.3:
                        severity = self._calculate_severity_from_ratio(change_ratio)
                        
                        if change_ratio > 3.0:
                            description = f"⚠️ Activity surge at {hour:02d}:00 - {w2_avg:.1f} files/hour vs {w1_avg:.1f} previously"
                        else:
                            description = f"⚠️ Activity drop at {hour:02d}:00 - {w2_avg:.1f} files/hour vs {w1_avg:.1f} previously"
                        
                        anomaly = Anomaly(
                            anomaly_id=f"trend_{hour:02d}_{datetime.now().strftime('%Y%m%d')}",
                            anomaly_type='trend',
                            severity=severity,
                            description=description,
                            data_points={
                                'hour': hour,
                                'current_avg': w2_avg,
                                'previous_avg': w1_avg,
                                'change_ratio': change_ratio,
                                'change_percent': ((w2_avg - w1_avg) / w1_avg) * 100
                            },
                            confidence=min(0.85, abs(change_ratio - 1.0) / 3.0),
                            detected_at=datetime.now()
                        )
                        anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting activity trend changes: {e}")
            return []
    
    def _detect_classification_anomalies(self) -> List[Anomaly]:
        """Detect anomalies in file classification patterns"""
        anomalies = []
        
        try:
            # Get classification accuracy over time
            classification_data = self._get_classification_accuracy(days=14)
            if len(classification_data) < 7:
                return anomalies
            
            df = pd.DataFrame(classification_data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Calculate rolling accuracy
            df['accuracy_7d'] = df['accuracy'].rolling(window=7, min_periods=3).mean()
            
            # Detect sudden drops in accuracy
            recent_accuracy = df['accuracy_7d'].iloc[-1] if not df['accuracy_7d'].isna().iloc[-1] else None
            baseline_accuracy = df['accuracy_7d'].iloc[:-3].mean() if len(df) > 3 else None
            
            if recent_accuracy is not None and baseline_accuracy is not None:
                accuracy_drop = baseline_accuracy - recent_accuracy
                
                if accuracy_drop > 0.15:  # 15% drop in accuracy
                    severity = 'high' if accuracy_drop > 0.25 else 'medium'
                    
                    description = f"⚠️ Classification accuracy drop: {recent_accuracy:.1%} vs {baseline_accuracy:.1%} baseline"
                    
                    anomaly = Anomaly(
                        anomaly_id=f"classification_{datetime.now().strftime('%Y%m%d')}",
                        anomaly_type='pattern',
                        severity=severity,
                        description=description,
                        data_points={
                            'current_accuracy': recent_accuracy,
                            'baseline_accuracy': baseline_accuracy,
                            'accuracy_drop': accuracy_drop,
                            'drop_percent': (accuracy_drop / baseline_accuracy) * 100
                        },
                        confidence=0.85,
                        detected_at=datetime.now()
                    )
                    anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting classification anomalies: {e}")
            return []
    
    def _get_recent_file_activity(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get recent file activity grouped by date"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # This would query the actual database
            # For now, return mock data structure
            files = self.db_manager.search_files(limit=5000)
            
            # Group by date
            daily_counts = defaultdict(int)
            for file_info in files:
                if file_info.get('created_at'):
                    try:
                        file_date = datetime.fromisoformat(file_info['created_at'][:10])
                        if file_date >= datetime.fromisoformat(cutoff_date[:10]):
                            daily_counts[file_date.date()] += 1
                    except:
                        continue
            
            return [{'date': date, 'count': count} for date, count in daily_counts.items()]
            
        except Exception as e:
            logger.error(f"Error getting recent file activity: {e}")
            return []
    
    def _get_file_type_distribution(self, days: int = 7, exclude_recent: int = 0) -> Dict[str, int]:
        """Get distribution of file types"""
        try:
            end_date = datetime.now() - timedelta(days=exclude_recent)
            start_date = end_date - timedelta(days=days)
            
            files = self.db_manager.search_files(limit=5000)
            
            type_counts = defaultdict(int)
            for file_info in files:
                if file_info.get('created_at'):
                    try:
                        file_date = datetime.fromisoformat(file_info['created_at'][:19])
                        if start_date <= file_date <= end_date:
                            file_ext = Path(file_info['path']).suffix.lower()
                            type_counts[file_ext or 'no_extension'] += 1
                    except:
                        continue
            
            return dict(type_counts)
            
        except Exception as e:
            logger.error(f"Error getting file type distribution: {e}")
            return {}
    
    def _get_hourly_activity(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get hourly activity data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            files = self.db_manager.search_files(limit=5000)
            
            hourly_counts = defaultdict(int)
            for file_info in files:
                if file_info.get('created_at'):
                    try:
                        file_datetime = datetime.fromisoformat(file_info['created_at'][:19])
                        if file_datetime >= cutoff_date:
                            # Round to hour
                            hour_key = file_datetime.replace(minute=0, second=0, microsecond=0)
                            hourly_counts[hour_key] += 1
                    except:
                        continue
            
            return [{'datetime': dt, 'count': count} for dt, count in hourly_counts.items()]
            
        except Exception as e:
            logger.error(f"Error getting hourly activity: {e}")
            return []
    
    def _get_classification_accuracy(self, days: int = 14) -> List[Dict[str, Any]]:
        """Get classification accuracy over time"""
        try:
            # This would calculate actual accuracy based on user feedback
            # For now, return mock structure
            dates = []
            current_date = datetime.now() - timedelta(days=days)
            
            while current_date <= datetime.now():
                # Simulate accuracy with some variation
                base_accuracy = 0.85
                variation = np.random.normal(0, 0.05)
                accuracy = np.clip(base_accuracy + variation, 0.5, 1.0)
                
                dates.append({
                    'date': current_date.date(),
                    'accuracy': accuracy,
                    'total_files': np.random.randint(10, 50)
                })
                current_date += timedelta(days=1)
            
            return dates
            
        except Exception as e:
            logger.error(f"Error getting classification accuracy: {e}")
            return []
    
    def _calculate_severity(self, value: float, low: float, medium: float, high: float) -> str:
        """Calculate severity based on thresholds"""
        if value >= high:
            return 'critical'
        elif value >= medium:
            return 'high'
        elif value >= low:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_severity_from_ratio(self, ratio: float) -> str:
        """Calculate severity from change ratio"""
        deviation = abs(ratio - 1.0)
        return self._calculate_severity(deviation, 1.0, 2.0, 4.0)
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def _save_anomaly(self, anomaly: Anomaly):
        """Save anomaly to database"""
        try:
            anomaly_db_path = Path.home() / ".automata02" / "anomalies.sqlite"
            with sqlite3.connect(str(anomaly_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO anomalies
                    (anomaly_id, anomaly_type, severity, description, data_points, 
                     confidence, detected_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    anomaly.anomaly_id,
                    anomaly.anomaly_type,
                    anomaly.severity,
                    anomaly.description,
                    json.dumps(anomaly.data_points),
                    anomaly.confidence,
                    anomaly.detected_at.isoformat(),
                    anomaly.status
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving anomaly: {e}")
    
    def get_active_anomalies(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get active anomalies"""
        try:
            anomaly_db_path = Path.home() / ".automata02" / "anomalies.sqlite"
            if not Path(anomaly_db_path).exists():
                return []
                
            with sqlite3.connect(str(anomaly_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT anomaly_id, anomaly_type, severity, description, 
                           data_points, confidence, detected_at, status
                    FROM anomalies
                    WHERE status = 'active'
                    ORDER BY detected_at DESC, severity DESC
                    LIMIT ?
                ''', (limit,))
                
                anomalies = []
                for row in cursor.fetchall():
                    anomalies.append({
                        'anomaly_id': row[0],
                        'anomaly_type': row[1],
                        'severity': row[2],
                        'description': row[3],
                        'data_points': json.loads(row[4] or '{}'),
                        'confidence': row[5],
                        'detected_at': row[6],
                        'status': row[7]
                    })
                
                return anomalies
                
        except Exception as e:
            logger.error(f"Error getting active anomalies: {e}")
            return []
    
    def resolve_anomaly(self, anomaly_id: str, resolution_notes: str = None) -> bool:
        """Mark anomaly as resolved"""
        try:
            anomaly_db_path = Path.home() / ".automata02" / "anomalies.sqlite"
            with sqlite3.connect(str(anomaly_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE anomalies 
                    SET status = 'resolved', resolved_at = ?, resolution_notes = ?
                    WHERE anomaly_id = ?
                ''', (datetime.now().isoformat(), resolution_notes, anomaly_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error resolving anomaly: {e}")
            return False
    
    def dismiss_anomaly(self, anomaly_id: str) -> bool:
        """Dismiss anomaly"""
        try:
            anomaly_db_path = Path.home() / ".automata02" / "anomalies.sqlite"
            with sqlite3.connect(str(anomaly_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE anomalies 
                    SET status = 'dismissed', resolved_at = ?
                    WHERE anomaly_id = ?
                ''', (datetime.now().isoformat(), anomaly_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error dismissing anomaly: {e}")
            return False
    
    def get_anomaly_stats(self) -> Dict[str, Any]:
        """Get anomaly detection statistics"""
        try:
            anomaly_db_path = Path.home() / ".automata02" / "anomalies.sqlite"
            if not Path(anomaly_db_path).exists():
                return {}
                
            with sqlite3.connect(str(anomaly_db_path)) as conn:
                cursor = conn.cursor()
                
                # Total anomalies
                cursor.execute('SELECT COUNT(*) FROM anomalies')
                total_anomalies = cursor.fetchone()[0]
                
                # Active anomalies
                cursor.execute('SELECT COUNT(*) FROM anomalies WHERE status = "active"')
                active_anomalies = cursor.fetchone()[0]
                
                # Anomalies by severity
                cursor.execute('''
                    SELECT severity, COUNT(*) 
                    FROM anomalies 
                    WHERE status = "active"
                    GROUP BY severity
                ''')
                severity_counts = dict(cursor.fetchall())
                
                # Anomalies by type
                cursor.execute('''
                    SELECT anomaly_type, COUNT(*) 
                    FROM anomalies 
                    WHERE status = "active"
                    GROUP BY anomaly_type
                ''')
                type_counts = dict(cursor.fetchall())
                
                return {
                    'total_anomalies': total_anomalies,
                    'active_anomalies': active_anomalies,
                    'severity_distribution': severity_counts,
                    'type_distribution': type_counts,
                    'last_detection': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting anomaly stats: {e}")
            return {}