"""
Behavioral Workflow Learning Module for AUTOMATA02.
Tracks user workflows across apps and learns patterns for automation suggestions.
"""

import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import psutil
from utils.logger import setup_logger

logger = setup_logger()

class WorkflowEvent:
    """Represents a workflow event (file operation, app action, etc.)"""
    
    def __init__(self, event_type: str, file_path: str = None, app_name: str = None, 
                 action: str = None, metadata: Dict[str, Any] = None):
        self.timestamp = datetime.now()
        self.event_type = event_type  # 'file_operation', 'app_action', 'user_command'
        self.file_path = file_path
        self.app_name = app_name
        self.action = action  # 'rename', 'move', 'open', 'export', etc.
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'file_path': self.file_path,
            'app_name': self.app_name,
            'action': self.action,
            'metadata': self.metadata
        }

class WorkflowPattern:
    """Represents a learned workflow pattern"""
    
    def __init__(self, pattern_id: str, sequence: List[str], confidence: float,
                 frequency: int, suggested_automation: str):
        self.pattern_id = pattern_id
        self.sequence = sequence  # List of actions in sequence
        self.confidence = confidence
        self.frequency = frequency
        self.suggested_automation = suggested_automation
        self.created_at = datetime.now()

class BehavioralWorkflowLearner:
    """Main class for learning user behavioral workflows"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.events_buffer = []
        self.buffer_lock = threading.Lock()
        self.patterns = {}
        self.session_events = []
        self.min_pattern_frequency = 3
        self.pattern_window_hours = 24
        
        # Initialize workflow database
        self._init_workflow_db()
        
        # Load existing patterns
        self._load_patterns()
        
        # Start background monitoring
        self.monitoring = False
        self.monitor_thread = None
    
    def _init_workflow_db(self):
        """Initialize workflow tracking database tables"""
        try:
            workflow_db_path = Path.home() / ".automata02" / "workflows.sqlite"
            
            with sqlite3.connect(str(workflow_db_path)) as conn:
                cursor = conn.cursor()
                
                # Events table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS workflow_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        file_path TEXT,
                        app_name TEXT,
                        action TEXT,
                        metadata TEXT,
                        session_id TEXT
                    )
                ''')
                
                # Patterns table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS workflow_patterns (
                        pattern_id TEXT PRIMARY KEY,
                        sequence TEXT NOT NULL,
                        confidence REAL,
                        frequency INTEGER,
                        suggested_automation TEXT,
                        created_at TEXT,
                        last_seen TEXT,
                        active BOOLEAN DEFAULT 1
                    )
                ''')
                
                # Pattern suggestions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS automation_suggestions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pattern_id TEXT,
                        suggestion_text TEXT,
                        confidence REAL,
                        created_at TEXT,
                        user_action TEXT,  -- 'accepted', 'rejected', 'pending'
                        FOREIGN KEY (pattern_id) REFERENCES workflow_patterns (pattern_id)
                    )
                ''')
                
                conn.commit()
                logger.info("Workflow learning database initialized")
                
        except Exception as e:
            logger.error(f"Error initializing workflow database: {e}")
    
    def start_monitoring(self):
        """Start behavioral monitoring"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
            self.monitor_thread.start()
            logger.info("Behavioral workflow monitoring started")
    
    def stop_monitoring(self):
        """Stop behavioral monitoring"""
        if self.monitoring:
            self.monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
            logger.info("Behavioral workflow monitoring stopped")
    
    def _monitor_system(self):
        """Background system monitoring for workflow events"""
        session_id = f"session_{int(time.time())}"
        
        while self.monitoring:
            try:
                # Monitor running processes for interesting patterns
                self._detect_app_workflows()
                
                # Process events buffer
                self._process_events_buffer()
                
                # Learn patterns periodically
                if len(self.session_events) > 5:
                    self._discover_patterns()
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in workflow monitoring: {e}")
                time.sleep(10)
    
    def _detect_app_workflows(self):
        """Detect application workflows and file operations"""
        try:
            # Get currently running processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    if proc_info['name'] and self._is_interesting_app(proc_info['name']):
                        # Log interesting app activities
                        event = WorkflowEvent(
                            event_type='app_action',
                            app_name=proc_info['name'],
                            action='running',
                            metadata={'cmdline': proc_info.get('cmdline', [])}
                        )
                        self._add_event(event)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.debug(f"Error detecting app workflows: {e}")
    
    def _is_interesting_app(self, app_name: str) -> bool:
        """Check if app is interesting for workflow learning"""
        interesting_apps = [
            'code', 'vscode', 'sublime', 'atom',  # Editors
            'excel', 'calc', 'libreoffice',      # Spreadsheets
            'word', 'writer',                     # Documents
            'chrome', 'firefox', 'safari',        # Browsers
            'slack', 'teams', 'discord',          # Communication
            'git', 'python', 'node'               # Development
        ]
        
        app_lower = app_name.lower()
        return any(interesting in app_lower for interesting in interesting_apps)
    
    def record_file_operation(self, operation: str, file_path: str, metadata: Dict[str, Any] = None):
        """Record a file operation for workflow learning"""
        event = WorkflowEvent(
            event_type='file_operation',
            file_path=file_path,
            action=operation,
            metadata=metadata
        )
        self._add_event(event)
        logger.debug(f"Recorded file operation: {operation} on {file_path}")
    
    def record_user_command(self, command: str, metadata: Dict[str, Any] = None):
        """Record a user command for workflow learning"""
        event = WorkflowEvent(
            event_type='user_command',
            action=command,
            metadata=metadata
        )
        self._add_event(event)
        logger.debug(f"Recorded user command: {command}")
    
    def _add_event(self, event: WorkflowEvent):
        """Add event to buffer and session"""
        with self.buffer_lock:
            self.events_buffer.append(event)
            self.session_events.append(event)
            
            # Keep session events within reasonable size
            if len(self.session_events) > 1000:
                self.session_events = self.session_events[-500:]
    
    def _process_events_buffer(self):
        """Process buffered events and save to database"""
        if not self.events_buffer:
            return
            
        with self.buffer_lock:
            events_to_process = self.events_buffer.copy()
            self.events_buffer.clear()
        
        # Save events to database
        try:
            workflow_db_path = Path.home() / ".automata02" / "workflows.sqlite"
            with sqlite3.connect(str(workflow_db_path)) as conn:
                cursor = conn.cursor()
                
                for event in events_to_process:
                    cursor.execute('''
                        INSERT INTO workflow_events 
                        (timestamp, event_type, file_path, app_name, action, metadata, session_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        event.timestamp.isoformat(),
                        event.event_type,
                        event.file_path,
                        event.app_name,
                        event.action,
                        json.dumps(event.metadata),
                        'current_session'
                    ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error processing events buffer: {e}")
    
    def _discover_patterns(self):
        """Discover patterns in recent workflow events"""
        try:
            # Analyze recent events for sequential patterns
            recent_events = self.session_events[-50:]  # Last 50 events
            
            # Group events by time windows
            sequences = self._extract_event_sequences(recent_events)
            
            # Find frequent patterns
            pattern_candidates = self._find_frequent_patterns(sequences)
            
            # Generate automation suggestions
            for pattern, frequency in pattern_candidates.items():
                if frequency >= self.min_pattern_frequency:
                    suggestion = self._generate_automation_suggestion(pattern)
                    if suggestion:
                        self._save_pattern(pattern, frequency, suggestion)
            
        except Exception as e:
            logger.error(f"Error discovering patterns: {e}")
    
    def _extract_event_sequences(self, events: List[WorkflowEvent]) -> List[List[str]]:
        """Extract sequences of actions from events"""
        sequences = []
        current_sequence = []
        last_time = None
        
        for event in events:
            # If more than 10 minutes passed, start new sequence
            if last_time and (event.timestamp - last_time).seconds > 600:
                if len(current_sequence) > 1:
                    sequences.append(current_sequence.copy())
                current_sequence = []
            
            action_signature = f"{event.event_type}:{event.action}"
            if event.file_path:
                file_ext = Path(event.file_path).suffix.lower()
                action_signature += f":{file_ext}"
            
            current_sequence.append(action_signature)
            last_time = event.timestamp
        
        if len(current_sequence) > 1:
            sequences.append(current_sequence)
        
        return sequences
    
    def _find_frequent_patterns(self, sequences: List[List[str]]) -> Dict[tuple, int]:
        """Find frequently occurring patterns in sequences"""
        pattern_counts = Counter()
        
        # Look for patterns of length 2-5
        for seq in sequences:
            for length in range(2, min(6, len(seq) + 1)):
                for i in range(len(seq) - length + 1):
                    pattern = tuple(seq[i:i+length])
                    pattern_counts[pattern] += 1
        
        return dict(pattern_counts)
    
    def _generate_automation_suggestion(self, pattern: tuple) -> Optional[str]:
        """Generate automation suggestion for a pattern"""
        pattern_str = " → ".join(pattern)
        
        # Common pattern suggestions
        if "file_operation:move" in pattern_str and "file_operation:rename" in pattern_str:
            return "Auto-organize files with similar names to designated folders"
        
        if "file_operation:created:.csv" in pattern_str and "file_operation:open" in pattern_str:
            return "Automatically generate summary reports for new CSV files"
        
        if "file_operation:created:.pdf" in pattern_str and "user_command" in pattern_str:
            return "Auto-classify and move PDF documents based on content"
        
        if "app_action:running" in pattern_str and "file_operation:export" in pattern_str:
            return f"Create automation recipe for {pattern_str.replace('app_action:running:', '').split(' ')[0]} workflows"
        
        # Generic suggestion
        return f"Create automation rule for pattern: {pattern_str}"
    
    def _save_pattern(self, pattern: tuple, frequency: int, suggestion: str):
        """Save discovered pattern to database"""
        try:
            pattern_id = f"pattern_{abs(hash(pattern))}"
            confidence = min(0.95, frequency / 10.0)  # Confidence based on frequency
            
            workflow_db_path = Path.home() / ".automata02" / "workflows.sqlite"
            with sqlite3.connect(str(workflow_db_path)) as conn:
                cursor = conn.cursor()
                
                # Check if pattern already exists
                cursor.execute('SELECT frequency FROM workflow_patterns WHERE pattern_id = ?', (pattern_id,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update frequency
                    new_frequency = existing[0] + frequency
                    cursor.execute('''
                        UPDATE workflow_patterns 
                        SET frequency = ?, last_seen = ?, confidence = ?
                        WHERE pattern_id = ?
                    ''', (new_frequency, datetime.now().isoformat(), 
                          min(0.95, new_frequency / 10.0), pattern_id))
                else:
                    # Insert new pattern
                    cursor.execute('''
                        INSERT INTO workflow_patterns 
                        (pattern_id, sequence, confidence, frequency, suggested_automation, 
                         created_at, last_seen)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        pattern_id,
                        json.dumps(list(pattern)),
                        confidence,
                        frequency,
                        suggestion,
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
                
                # Add automation suggestion
                cursor.execute('''
                    INSERT INTO automation_suggestions 
                    (pattern_id, suggestion_text, confidence, created_at, user_action)
                    VALUES (?, ?, ?, ?, ?)
                ''', (pattern_id, suggestion, confidence, datetime.now().isoformat(), 'pending'))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving pattern: {e}")
    
    def get_automation_suggestions(self) -> List[Dict[str, Any]]:
        """Get pending automation suggestions"""
        try:
            workflow_db_path = Path.home() / ".automata02" / "workflows.sqlite"
            with sqlite3.connect(str(workflow_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT s.id, s.pattern_id, s.suggestion_text, s.confidence, 
                           s.created_at, p.frequency, p.sequence
                    FROM automation_suggestions s
                    JOIN workflow_patterns p ON s.pattern_id = p.pattern_id
                    WHERE s.user_action = 'pending'
                    ORDER BY s.confidence DESC, p.frequency DESC
                    LIMIT 10
                ''')
                
                suggestions = []
                for row in cursor.fetchall():
                    suggestions.append({
                        'id': row[0],
                        'pattern_id': row[1],
                        'suggestion': row[2],
                        'confidence': row[3],
                        'created_at': row[4],
                        'frequency': row[5],
                        'sequence': json.loads(row[6])
                    })
                
                return suggestions
                
        except Exception as e:
            logger.error(f"Error getting automation suggestions: {e}")
            return []
    
    def accept_suggestion(self, suggestion_id: int) -> bool:
        """Accept an automation suggestion"""
        return self._update_suggestion_status(suggestion_id, 'accepted')
    
    def reject_suggestion(self, suggestion_id: int) -> bool:
        """Reject an automation suggestion"""
        return self._update_suggestion_status(suggestion_id, 'rejected')
    
    def _update_suggestion_status(self, suggestion_id: int, status: str) -> bool:
        """Update suggestion status"""
        try:
            workflow_db_path = Path.home() / ".automata02" / "workflows.sqlite"
            with sqlite3.connect(str(workflow_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE automation_suggestions 
                    SET user_action = ? 
                    WHERE id = ?
                ''', (status, suggestion_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating suggestion status: {e}")
            return False
    
    def get_workflow_stats(self) -> Dict[str, Any]:
        """Get workflow learning statistics"""
        try:
            workflow_db_path = Path.home() / ".automata02" / "workflows.sqlite"
            with sqlite3.connect(str(workflow_db_path)) as conn:
                cursor = conn.cursor()
                
                # Total events
                cursor.execute('SELECT COUNT(*) FROM workflow_events')
                total_events = cursor.fetchone()[0]
                
                # Patterns discovered
                cursor.execute('SELECT COUNT(*) FROM workflow_patterns WHERE active = 1')
                patterns_discovered = cursor.fetchone()[0]
                
                # Pending suggestions
                cursor.execute('SELECT COUNT(*) FROM automation_suggestions WHERE user_action = "pending"')
                pending_suggestions = cursor.fetchone()[0]
                
                # Recent activity (last 24h)
                yesterday = (datetime.now() - timedelta(days=1)).isoformat()
                cursor.execute('SELECT COUNT(*) FROM workflow_events WHERE timestamp > ?', (yesterday,))
                recent_activity = cursor.fetchone()[0]
                
                return {
                    'total_events': total_events,
                    'patterns_discovered': patterns_discovered,
                    'pending_suggestions': pending_suggestions,
                    'recent_activity': recent_activity,
                    'monitoring_active': self.monitoring
                }
                
        except Exception as e:
            logger.error(f"Error getting workflow stats: {e}")
            return {
                'total_events': 0,
                'patterns_discovered': 0,
                'pending_suggestions': 0,
                'recent_activity': 0,
                'monitoring_active': self.monitoring
            }
    
    def _load_patterns(self):
        """Load existing patterns from database"""
        try:
            workflow_db_path = Path.home() / ".automata02" / "workflows.sqlite"
            if not Path(workflow_db_path).exists():
                return
                
            with sqlite3.connect(str(workflow_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT pattern_id, sequence, confidence FROM workflow_patterns WHERE active = 1')
                
                for row in cursor.fetchall():
                    pattern_id, sequence_json, confidence = row
                    sequence = json.loads(sequence_json)
                    self.patterns[pattern_id] = {
                        'sequence': sequence,
                        'confidence': confidence
                    }
                
                logger.info(f"Loaded {len(self.patterns)} workflow patterns")
                
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")