import sqlite3
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
from utils.logger import setup_logger

logger = setup_logger()

class DatabaseManager:
    """Manages SQLite database operations for file inventory."""
    
    def __init__(self, db_path: str | None = None):
        """Initialize database manager."""
        if db_path is None:
            # Create .automata02 directory in user home
            home_dir = Path.home()
            automata_dir = home_dir / ".automata02"
            automata_dir.mkdir(exist_ok=True)
            db_path = automata_dir / "automata02.sqlite"
        
        self.db_path = str(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create inventory table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS inventory (
                        id TEXT PRIMARY KEY,
                        abs_path TEXT NOT NULL UNIQUE,
                        rel_path TEXT,
                        sha256 TEXT,
                        size_bytes INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        modified_at TIMESTAMP,
                        mime_type TEXT,
                        label TEXT,
                        tags TEXT, -- JSON array
                        extracted_text_path TEXT,
                        meta_json TEXT -- JSON metadata
                    )
                ''')
                
                # Create rules table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS rules (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        priority INTEGER DEFAULT 100,
                        when_conditions TEXT, -- JSON
                        then_actions TEXT, -- JSON
                        active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create activity log table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS activity_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        action TEXT,
                        file_path TEXT,
                        details TEXT, -- JSON
                        status TEXT DEFAULT 'success'
                    )
                ''')
                
                # Create indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_label ON inventory(label)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_created ON inventory(created_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp)')
                
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def add_file(self, file_path: str, label: str = "other", tags: List[str] | None = None, 
                 mime_type: str | None = None, metadata: Dict[str, Any] | None = None) -> str:
        """Add file to inventory."""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Generate file hash
            file_id = self._generate_file_id(str(file_path_obj))
            file_hash = self._calculate_file_hash(str(file_path_obj))
            
            # Get file stats
            stat = file_path_obj.stat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO inventory 
                    (id, abs_path, rel_path, sha256, size_bytes, created_at, 
                     modified_at, mime_type, label, tags, meta_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file_id,
                    str(file_path_obj.absolute()),
                    str(file_path_obj.relative_to(Path.home())) if str(file_path_obj).startswith(str(Path.home())) else str(file_path_obj),
                    file_hash,
                    stat.st_size,
                    datetime.now().isoformat(),
                    datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    mime_type,
                    label,
                    json.dumps(tags or []),
                    json.dumps(metadata or {})
                ))
                
                conn.commit()
                
                # Log activity
                self.log_activity("file_added", str(file_path), {
                    "label": label,
                    "tags": tags,
                    "size": stat.st_size
                })
                
                logger.info(f"File added to inventory: {file_path_obj}")
                return file_id
                
        except Exception as e:
            logger.error(f"Error adding file to inventory: {e}")
            self.log_activity("file_add_failed", str(file_path), {"error": str(e)}, "error")
            raise
    
    def update_file_location(self, old_path: str, new_path: str):
        """Update file location in inventory."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE inventory 
                    SET abs_path = ?, rel_path = ?, modified_at = ?
                    WHERE abs_path = ?
                ''', (
                    new_path,
                    str(Path(new_path).relative_to(Path.home())) if new_path.startswith(str(Path.home())) else new_path,
                    datetime.now().isoformat(),
                    old_path
                ))
                
                conn.commit()
                
                self.log_activity("file_moved", old_path, {
                    "new_path": new_path
                })
                
                logger.info(f"File location updated: {old_path} -> {new_path}")
                
        except Exception as e:
            logger.error(f"Error updating file location: {e}")
            self.log_activity("file_move_failed", old_path, {"error": str(e)}, "error")
            raise
    
    def get_recent_files(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently added files."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT abs_path, label, tags, created_at, size_bytes
                    FROM inventory 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
                
                files = []
                for row in cursor.fetchall():
                    files.append({
                        'path': row[0],
                        'label': row[1],
                        'tags': json.loads(row[2] or '[]'),
                        'created_at': row[3],
                        'size_bytes': row[4]
                    })
                
                return files
                
        except Exception as e:
            logger.error(f"Error getting recent files: {e}")
            return []
    
    def search_files(self, query: str | None = None, label: str | None = None, 
                     tags: List[str] | None = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Search files in inventory."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                sql = 'SELECT * FROM inventory WHERE 1=1'
                params = []
                
                if query:
                    sql += ' AND (abs_path LIKE ? OR label LIKE ?)'
                    params.extend([f'%{query}%', f'%{query}%'])
                
                if label:
                    sql += ' AND label = ?'
                    params.append(label)
                
                if tags:
                    for tag in tags:
                        sql += ' AND tags LIKE ?'
                        params.append(f'%"{tag}"%')
                
                sql += ' ORDER BY created_at DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(sql, params)
                
                files = []
                for row in cursor.fetchall():
                    files.append({
                        'id': row[0],
                        'path': row[1],
                        'relative_path': row[2],
                        'hash': row[3],
                        'size_bytes': row[4],
                        'created_at': row[5],
                        'modified_at': row[6],
                        'mime_type': row[7],
                        'label': row[8],
                        'tags': json.loads(row[9] or '[]'),
                        'extracted_text_path': row[10],
                        'metadata': json.loads(row[11] or '{}')
                    })
                
                return files
                
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return []
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get statistics for dashboard."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total files
                cursor.execute('SELECT COUNT(*) FROM inventory')
                total_files = cursor.fetchone()[0]
                
                # Files today
                today = datetime.now().date().isoformat()
                cursor.execute('SELECT COUNT(*) FROM inventory WHERE DATE(created_at) = ?', (today,))
                files_today = cursor.fetchone()[0]
                
                # Unique labels
                cursor.execute('SELECT COUNT(DISTINCT label) FROM inventory')
                unique_labels = cursor.fetchone()[0]
                
                return {
                    'total_files': total_files,
                    'files_today': files_today,
                    'unique_labels': unique_labels
                }
                
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {'total_files': 0, 'files_today': 0, 'unique_labels': 0}
    
    def get_category_distribution(self) -> Dict[str, int]:
        """Get distribution of files by category."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT label, COUNT(*) 
                    FROM inventory 
                    GROUP BY label 
                    ORDER BY COUNT(*) DESC
                ''')
                
                return dict(cursor.fetchall())
                
        except Exception as e:
            logger.error(f"Error getting category distribution: {e}")
            return {}
    
    def log_activity(self, action: str, file_path: str, details: Dict[str, Any], 
                     status: str = "success"):
        """Log system activity."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO activity_log (action, file_path, details, status)
                    VALUES (?, ?, ?, ?)
                ''', (action, file_path, json.dumps(details), status))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
    
    def get_activity_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent activity log entries."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT timestamp, action, file_path, details, status
                    FROM activity_log
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                activities = []
                for row in cursor.fetchall():
                    activities.append({
                        'timestamp': row[0],
                        'action': row[1],
                        'file_path': row[2],
                        'details': json.loads(row[3] or '{}'),
                        'status': row[4]
                    })
                
                return activities
                
        except Exception as e:
            logger.error(f"Error getting activity log: {e}")
            return []
    
    def _generate_file_id(self, file_path: str) -> str:
        """Generate unique ID for file."""
        return hashlib.md5(file_path.encode()).hexdigest()
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file."""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return ""
