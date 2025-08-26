"""
Autonomous Scheduling Module for AUTOMATA02.
Handles automated task scheduling and execution.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import threading
from utils.logger import setup_logger

logger = setup_logger()

class ScheduledTask:
    """Represents a scheduled automation task"""
    
    def __init__(self, task_id: str, name: str, task_type: str, 
                 schedule: str, parameters: Dict[str, Any],
                 enabled: bool = True, notifications: bool = True):
        self.task_id = task_id
        self.name = name
        self.task_type = task_type
        self.schedule = schedule
        self.parameters = parameters
        self.enabled = enabled
        self.notifications = notifications
        self.created_at = datetime.now()
        self.last_run = None
        self.next_run = None
        self.run_count = 0
        self.success_count = 0
        self.error_count = 0

class AutonomousScheduler:
    """Main scheduler for autonomous task execution"""
    
    def __init__(self, db_manager, config_manager):
        self.db_manager = db_manager
        self.config_manager = config_manager
        
        # Initialize scheduler database
        self._init_scheduler_db()
        
        # Set up APScheduler
        self.scheduler = None
        self.running = False
        self.tasks = {}
        
        # Task handlers
        self.task_handlers = {
            'file_organization': self._handle_file_organization,
            'report_generation': self._handle_report_generation,
            'data_backup': self._handle_data_backup,
            'cleanup': self._handle_cleanup,
            'notification': self._handle_notification,
            'data_analysis': self._handle_data_analysis,
            'file_sync': self._handle_file_sync,
            'system_maintenance': self._handle_system_maintenance
        }
        
        # Notification methods
        self.notification_methods = {
            'system': self._send_system_notification,
            'log': self._send_log_notification,
            'email': self._send_email_notification,
            'slack': self._send_slack_notification
        }
        
        self._setup_scheduler()
        self._load_existing_tasks()
    
    def _init_scheduler_db(self):
        """Initialize scheduler database tables"""
        try:
            scheduler_db_path = Path.home() / ".automata02" / "scheduler.sqlite"
            
            with sqlite3.connect(str(scheduler_db_path)) as conn:
                cursor = conn.cursor()
                
                # Scheduled tasks table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scheduled_tasks (
                        task_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        task_type TEXT NOT NULL,
                        schedule TEXT NOT NULL,
                        parameters TEXT,
                        enabled BOOLEAN DEFAULT 1,
                        notifications BOOLEAN DEFAULT 1,
                        created_at TEXT,
                        last_run TEXT,
                        next_run TEXT,
                        run_count INTEGER DEFAULT 0,
                        success_count INTEGER DEFAULT 0,
                        error_count INTEGER DEFAULT 0
                    )
                ''')
                
                # Task execution history
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS task_executions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT,
                        started_at TEXT,
                        completed_at TEXT,
                        success BOOLEAN,
                        result TEXT,
                        error_message TEXT,
                        execution_time_ms INTEGER,
                        FOREIGN KEY (task_id) REFERENCES scheduled_tasks (task_id)
                    )
                ''')
                
                # Task policies table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS task_policies (
                        policy_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        conditions TEXT,  -- JSON
                        actions TEXT,     -- JSON
                        enabled BOOLEAN DEFAULT 1,
                        created_at TEXT
                    )
                ''')
                
                conn.commit()
                logger.info("Scheduler database initialized")
                
        except Exception as e:
            logger.error(f"Error initializing scheduler database: {e}")
    
    def _setup_scheduler(self):
        """Set up APScheduler with proper configuration"""
        try:
            # Configure job store
            jobstore_url = f"sqlite:///{Path.home() / '.automata02' / 'scheduler.sqlite'}"
            jobstores = {
                'default': SQLAlchemyJobStore(url=jobstore_url)
            }
            
            # Configure executors
            executors = {
                'default': ThreadPoolExecutor(max_workers=3)
            }
            
            # Job defaults
            job_defaults = {
                'coalesce': False,
                'max_instances': 1,
                'misfire_grace_time': 300  # 5 minutes
            }
            
            # Create scheduler
            self.scheduler = BackgroundScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='local'
            )
            
            logger.info("APScheduler configured successfully")
            
        except Exception as e:
            logger.error(f"Error setting up scheduler: {e}")
    
    def start_scheduler(self):
        """Start the autonomous scheduler"""
        try:
            if not self.running and self.scheduler:
                self.scheduler.start()
                self.running = True
                logger.info("Autonomous scheduler started")
                return True
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
        return False
    
    def stop_scheduler(self):
        """Stop the autonomous scheduler"""
        try:
            if self.running and self.scheduler:
                self.scheduler.shutdown()
                self.running = False
                logger.info("Autonomous scheduler stopped")
                return True
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
        return False
    
    def add_task(self, name: str, task_type: str, schedule: str, 
                 parameters: Dict[str, Any], enabled: bool = True,
                 notifications: bool = True) -> str:
        """Add a new scheduled task"""
        try:
            task_id = f"task_{int(datetime.now().timestamp())}"
            
            task = ScheduledTask(
                task_id=task_id,
                name=name,
                task_type=task_type,
                schedule=schedule,
                parameters=parameters,
                enabled=enabled,
                notifications=notifications
            )
            
            # Save to database
            self._save_task(task)
            
            # Add to scheduler if enabled
            if enabled:
                self._schedule_task(task)
            
            self.tasks[task_id] = task
            logger.info(f"Added scheduled task: {name}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"Error adding task: {e}")
            return ""
    
    def _save_task(self, task: ScheduledTask):
        """Save task to database"""
        try:
            scheduler_db_path = Path.home() / ".automata02" / "scheduler.sqlite"
            with sqlite3.connect(str(scheduler_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO scheduled_tasks
                    (task_id, name, task_type, schedule, parameters, enabled, 
                     notifications, created_at, last_run, next_run, run_count, 
                     success_count, error_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.task_id,
                    task.name,
                    task.task_type,
                    task.schedule,
                    json.dumps(task.parameters),
                    task.enabled,
                    task.notifications,
                    task.created_at.isoformat(),
                    task.last_run.isoformat() if task.last_run else None,
                    task.next_run.isoformat() if task.next_run else None,
                    task.run_count,
                    task.success_count,
                    task.error_count
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving task: {e}")
    
    def _schedule_task(self, task: ScheduledTask):
        """Schedule a task with APScheduler"""
        try:
            if not self.scheduler:
                return
            
            # Parse schedule
            trigger = self._parse_schedule(task.schedule)
            if not trigger:
                logger.error(f"Invalid schedule format: {task.schedule}")
                return
            
            # Add job to scheduler
            self.scheduler.add_job(
                func=self._execute_task,
                trigger=trigger,
                args=[task.task_id],
                id=task.task_id,
                name=task.name,
                replace_existing=True
            )
            
            # Update next run time
            job = self.scheduler.get_job(task.task_id)
            if job:
                task.next_run = job.next_run_time.replace(tzinfo=None) if job.next_run_time else None
                self._save_task(task)
            
            logger.info(f"Scheduled task: {task.name} with schedule: {task.schedule}")
            
        except Exception as e:
            logger.error(f"Error scheduling task {task.name}: {e}")
    
    def _parse_schedule(self, schedule: str):
        """Parse schedule string into APScheduler trigger"""
        try:
            schedule = schedule.lower().strip()
            
            # Handle interval schedules
            if 'every' in schedule:
                if 'minute' in schedule:
                    minutes = self._extract_number(schedule)
                    return IntervalTrigger(minutes=minutes or 1)
                elif 'hour' in schedule:
                    hours = self._extract_number(schedule)
                    return IntervalTrigger(hours=hours or 1)
                elif 'day' in schedule:
                    days = self._extract_number(schedule)
                    return IntervalTrigger(days=days or 1)
                elif 'week' in schedule:
                    weeks = self._extract_number(schedule)
                    return IntervalTrigger(weeks=weeks or 1)
            
            # Handle cron-like schedules
            if 'daily' in schedule:
                time_match = self._extract_time(schedule)
                if time_match:
                    hour, minute = time_match
                    return CronTrigger(hour=hour, minute=minute)
                return CronTrigger(hour=9, minute=0)  # Default 9 AM
            
            elif 'weekly' in schedule:
                day = self._extract_weekday(schedule)
                time_match = self._extract_time(schedule)
                hour, minute = time_match if time_match else (18, 0)  # Default Friday 6 PM
                return CronTrigger(day_of_week=day or 4, hour=hour, minute=minute)
            
            elif 'monthly' in schedule:
                day = self._extract_number(schedule) or 1
                time_match = self._extract_time(schedule)
                hour, minute = time_match if time_match else (9, 0)
                return CronTrigger(day=day, hour=hour, minute=minute)
            
            # Handle specific day schedules
            weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            for i, day in enumerate(weekdays):
                if day in schedule:
                    time_match = self._extract_time(schedule)
                    hour, minute = time_match if time_match else (18, 0)
                    return CronTrigger(day_of_week=i, hour=hour, minute=minute)
            
            # Try to parse as cron expression
            if len(schedule.split()) == 5:
                return CronTrigger.from_crontab(schedule)
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing schedule '{schedule}': {e}")
            return None
    
    def _extract_number(self, text: str) -> Optional[int]:
        """Extract number from text"""
        import re
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else None
    
    def _extract_time(self, text: str) -> Optional[tuple]:
        """Extract time from text (hour, minute)"""
        import re
        # Look for time patterns like "5:30 PM", "17:30", "5PM"
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)?',
            r'(\d{1,2})\s*(am|pm)',
            r'(\d{1,2}):(\d{2})'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else 0
                
                # Handle AM/PM
                if len(match.groups()) > 2 and match.group(3):
                    if match.group(3).lower() == 'pm' and hour != 12:
                        hour += 12
                    elif match.group(3).lower() == 'am' and hour == 12:
                        hour = 0
                
                return (hour, minute)
        
        return None
    
    def _extract_weekday(self, text: str) -> Optional[int]:
        """Extract weekday from text (0=Monday, 6=Sunday)"""
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(weekdays):
            if day in text.lower():
                return i
        return None
    
    def _execute_task(self, task_id: str):
        """Execute a scheduled task"""
        start_time = datetime.now()
        
        try:
            task = self.tasks.get(task_id)
            if not task or not task.enabled:
                return
            
            logger.info(f"Executing scheduled task: {task.name}")
            
            # Execute the task
            handler = self.task_handlers.get(task.task_type)
            if handler:
                result = handler(task.parameters)
                success = True
                error_message = None
            else:
                result = f"No handler for task type: {task.task_type}"
                success = False
                error_message = result
            
            # Update task statistics
            task.run_count += 1
            task.last_run = start_time
            if success:
                task.success_count += 1
            else:
                task.error_count += 1
            
            # Update next run time
            job = self.scheduler.get_job(task_id)
            if job:
                task.next_run = job.next_run_time.replace(tzinfo=None) if job.next_run_time else None
            
            # Save updated task
            self._save_task(task)
            
            # Log execution
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            self._log_execution(task_id, start_time, datetime.now(), success, result, error_message, execution_time)
            
            # Send notification if enabled
            if task.notifications:
                self._send_task_notification(task, success, result, error_message)
            
            logger.info(f"Task {task.name} completed successfully" if success else f"Task {task.name} failed: {error_message}")
            
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            # Log failed execution
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            self._log_execution(task_id, start_time, datetime.now(), False, None, str(e), execution_time)
    
    def _log_execution(self, task_id: str, started_at: datetime, completed_at: datetime,
                      success: bool, result: str, error_message: str, execution_time: int):
        """Log task execution to database"""
        try:
            scheduler_db_path = Path.home() / ".automata02" / "scheduler.sqlite"
            with sqlite3.connect(str(scheduler_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO task_executions
                    (task_id, started_at, completed_at, success, result, error_message, execution_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task_id,
                    started_at.isoformat(),
                    completed_at.isoformat(),
                    success,
                    result,
                    error_message,
                    execution_time
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error logging task execution: {e}")
    
    def _send_task_notification(self, task: ScheduledTask, success: bool, result: str, error_message: str):
        """Send notification about task execution"""
        try:
            status = "completed successfully" if success else "failed"
            message = f"Scheduled task '{task.name}' {status}"
            
            if success and result:
                message += f"\nResult: {result}"
            elif error_message:
                message += f"\nError: {error_message}"
            
            # Send system notification by default
            self._send_system_notification(message)
            
        except Exception as e:
            logger.error(f"Error sending task notification: {e}")
    
    # Task Handlers
    def _handle_file_organization(self, parameters: Dict[str, Any]) -> str:
        """Handle file organization task"""
        try:
            target_path = parameters.get('target_path', 'all')
            apply_rules = parameters.get('apply_rules', True)
            
            # Get files to organize
            if target_path == 'all':
                # Organize all unorganized files
                files = self.db_manager.search_files(limit=1000)
            else:
                # Organize files in specific path
                files = [f for f in self.db_manager.search_files(limit=1000) 
                        if target_path in f.get('path', '')]
            
            organized_count = 0
            # This would integrate with the file organizer
            # organized_count = self.file_organizer.organize_files(files)
            
            return f"Organized {organized_count} files"
            
        except Exception as e:
            raise Exception(f"File organization failed: {e}")
    
    def _handle_report_generation(self, parameters: Dict[str, Any]) -> str:
        """Handle report generation task"""
        try:
            report_type = parameters.get('report_type', 'general')
            timeframe = parameters.get('timeframe', 'week')
            format_type = parameters.get('format', 'html')
            
            # Generate report (this would integrate with report generator)
            report_path = f"/tmp/report_{report_type}_{timeframe}.{format_type}"
            
            return f"Generated {report_type} report for {timeframe} period: {report_path}"
            
        except Exception as e:
            raise Exception(f"Report generation failed: {e}")
    
    def _handle_data_backup(self, parameters: Dict[str, Any]) -> str:
        """Handle data backup task"""
        try:
            backup_type = parameters.get('backup_type', 'incremental')
            destination = parameters.get('destination', 'local')
            
            # Perform backup
            backup_size = "1.2GB"  # Mock implementation
            
            return f"Completed {backup_type} backup to {destination} ({backup_size})"
            
        except Exception as e:
            raise Exception(f"Data backup failed: {e}")
    
    def _handle_cleanup(self, parameters: Dict[str, Any]) -> str:
        """Handle cleanup task"""
        try:
            cleanup_type = parameters.get('cleanup_type', 'temp_files')
            max_age_days = parameters.get('max_age_days', 30)
            
            # Perform cleanup
            cleaned_count = 42  # Mock implementation
            
            return f"Cleaned up {cleaned_count} {cleanup_type} older than {max_age_days} days"
            
        except Exception as e:
            raise Exception(f"Cleanup failed: {e}")
    
    def _handle_notification(self, parameters: Dict[str, Any]) -> str:
        """Handle notification task"""
        try:
            message = parameters.get('message', 'Scheduled notification')
            method = parameters.get('method', 'system')
            
            notification_func = self.notification_methods.get(method, self._send_system_notification)
            notification_func(message)
            
            return f"Sent notification via {method}"
            
        except Exception as e:
            raise Exception(f"Notification failed: {e}")
    
    def _handle_data_analysis(self, parameters: Dict[str, Any]) -> str:
        """Handle data analysis task"""
        try:
            analysis_type = parameters.get('analysis_type', 'general')
            data_source = parameters.get('data_source', 'files')
            
            # Perform analysis
            insights_count = 5  # Mock implementation
            
            return f"Completed {analysis_type} analysis on {data_source}, found {insights_count} insights"
            
        except Exception as e:
            raise Exception(f"Data analysis failed: {e}")
    
    def _handle_file_sync(self, parameters: Dict[str, Any]) -> str:
        """Handle file synchronization task"""
        try:
            source = parameters.get('source', 'local')
            destination = parameters.get('destination', 'cloud')
            
            # Perform sync
            synced_count = 15  # Mock implementation
            
            return f"Synchronized {synced_count} files from {source} to {destination}"
            
        except Exception as e:
            raise Exception(f"File sync failed: {e}")
    
    def _handle_system_maintenance(self, parameters: Dict[str, Any]) -> str:
        """Handle system maintenance task"""
        try:
            maintenance_type = parameters.get('maintenance_type', 'database_optimization')
            
            # Perform maintenance
            return f"Completed {maintenance_type} maintenance"
            
        except Exception as e:
            raise Exception(f"System maintenance failed: {e}")
    
    # Notification Methods
    def _send_system_notification(self, message: str):
        """Send system notification"""
        logger.info(f"System notification: {message}")
    
    def _send_log_notification(self, message: str):
        """Send log notification"""
        logger.info(f"Log notification: {message}")
    
    def _send_email_notification(self, message: str):
        """Send email notification"""
        logger.info(f"Email notification: {message}")
        # This would integrate with email service
    
    def _send_slack_notification(self, message: str):
        """Send Slack notification"""
        logger.info(f"Slack notification: {message}")
        # This would integrate with Slack API
    
    def _load_existing_tasks(self):
        """Load existing tasks from database"""
        try:
            scheduler_db_path = Path.home() / ".automata02" / "scheduler.sqlite"
            if not Path(scheduler_db_path).exists():
                return
                
            with sqlite3.connect(str(scheduler_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM scheduled_tasks WHERE enabled = 1')
                
                for row in cursor.fetchall():
                    task = ScheduledTask(
                        task_id=row[0],
                        name=row[1],
                        task_type=row[2],
                        schedule=row[3],
                        parameters=json.loads(row[4] or '{}'),
                        enabled=bool(row[5]),
                        notifications=bool(row[6])
                    )
                    
                    task.created_at = datetime.fromisoformat(row[7]) if row[7] else datetime.now()
                    task.last_run = datetime.fromisoformat(row[8]) if row[8] else None
                    task.next_run = datetime.fromisoformat(row[9]) if row[9] else None
                    task.run_count = row[10] or 0
                    task.success_count = row[11] or 0
                    task.error_count = row[12] or 0
                    
                    self.tasks[task.task_id] = task
                    
                    # Schedule the task
                    if task.enabled:
                        self._schedule_task(task)
                
                logger.info(f"Loaded {len(self.tasks)} scheduled tasks")
                
        except Exception as e:
            logger.error(f"Error loading existing tasks: {e}")
    
    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get all scheduled tasks"""
        return [
            {
                'task_id': task.task_id,
                'name': task.name,
                'task_type': task.task_type,
                'schedule': task.schedule,
                'enabled': task.enabled,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None,
                'run_count': task.run_count,
                'success_count': task.success_count,
                'error_count': task.error_count
            }
            for task in self.tasks.values()
        ]
    
    def get_task_executions(self, task_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution history for a task"""
        try:
            scheduler_db_path = Path.home() / ".automata02" / "scheduler.sqlite"
            with sqlite3.connect(str(scheduler_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT started_at, completed_at, success, result, error_message, execution_time_ms
                    FROM task_executions
                    WHERE task_id = ?
                    ORDER BY started_at DESC
                    LIMIT ?
                ''', (task_id, limit))
                
                executions = []
                for row in cursor.fetchall():
                    executions.append({
                        'started_at': row[0],
                        'completed_at': row[1],
                        'success': bool(row[2]),
                        'result': row[3],
                        'error_message': row[4],
                        'execution_time_ms': row[5]
                    })
                
                return executions
                
        except Exception as e:
            logger.error(f"Error getting task executions: {e}")
            return []
    
    def enable_task(self, task_id: str) -> bool:
        """Enable a scheduled task"""
        task = self.tasks.get(task_id)
        if task:
            task.enabled = True
            self._save_task(task)
            self._schedule_task(task)
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """Disable a scheduled task"""
        task = self.tasks.get(task_id)
        if task:
            task.enabled = False
            self._save_task(task)
            try:
                self.scheduler.remove_job(task_id)
            except:
                pass  # Job might not exist
            return True
        return False
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a scheduled task"""
        if task_id in self.tasks:
            try:
                self.scheduler.remove_job(task_id)
            except:
                pass  # Job might not exist
            
            del self.tasks[task_id]
            
            # Remove from database
            try:
                scheduler_db_path = Path.home() / ".automata02" / "scheduler.sqlite"
                with sqlite3.connect(str(scheduler_db_path)) as conn:
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM scheduled_tasks WHERE task_id = ?', (task_id,))
                    cursor.execute('DELETE FROM task_executions WHERE task_id = ?', (task_id,))
                    conn.commit()
            except Exception as e:
                logger.error(f"Error deleting task from database: {e}")
            
            return True
        return False
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        total_tasks = len(self.tasks)
        enabled_tasks = sum(1 for task in self.tasks.values() if task.enabled)
        total_runs = sum(task.run_count for task in self.tasks.values())
        total_successes = sum(task.success_count for task in self.tasks.values())
        
        return {
            'running': self.running,
            'total_tasks': total_tasks,
            'enabled_tasks': enabled_tasks,
            'disabled_tasks': total_tasks - enabled_tasks,
            'total_runs': total_runs,
            'total_successes': total_successes,
            'success_rate': (total_successes / total_runs * 100) if total_runs > 0 else 0
        }