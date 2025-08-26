import os
import threading
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent
from typing import List
from utils.logger import setup_logger
from core.classifier import FileClassifier
from core.organizer import FileOrganizer

logger = setup_logger()

class FileWatcherHandler(FileSystemEventHandler):
    """Handle file system events."""
    
    def __init__(self, db_manager, config_manager):
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.classifier = FileClassifier(config_manager)
        self.organizer = FileOrganizer(db_manager, config_manager)
        self._debounce_events = {}
        self._debounce_delay = 2.0  # 2 second debounce
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self._debounce_event('created', str(event.src_path))
    
    def on_moved(self, event):
        """Handle file move events."""
        if not event.is_directory:
            self._debounce_event('moved', str(event.dest_path), str(event.src_path))
    
    def _debounce_event(self, event_type: str, file_path: str, old_path: str | None = None):
        """Debounce file events to avoid processing rapid changes."""
        event_key = f"{event_type}:{file_path}"
        
        # Cancel previous timer for this event
        if event_key in self._debounce_events:
            self._debounce_events[event_key].cancel()
        
        # Create new timer
        timer = threading.Timer(
            self._debounce_delay,
            self._process_event,
            args=(event_type, file_path, old_path)
        )
        self._debounce_events[event_key] = timer
        timer.start()
    
    def _process_event(self, event_type: str, file_path: str, old_path: str | None = None):
        """Process debounced file event."""
        try:
            event_key = f"{event_type}:{file_path}"
            if event_key in self._debounce_events:
                del self._debounce_events[event_key]
            
            # Check if file still exists
            if not os.path.exists(file_path):
                logger.warning(f"File no longer exists: {file_path}")
                return
            
            # Skip temporary files and system files
            if self._should_ignore_file(file_path):
                return
            
            logger.info(f"Processing {event_type} event: {file_path}")
            
            if event_type == 'created':
                self._handle_file_created(file_path)
            elif event_type == 'moved':
                self._handle_file_moved(old_path, file_path)
                
        except Exception as e:
            logger.error(f"Error processing event {event_type} for {file_path}: {e}")
    
    def _should_ignore_file(self, file_path: str) -> bool:
        """Check if file should be ignored."""
        file_path_obj = Path(file_path)
        
        # Ignore hidden files, temp files, and system files
        ignore_patterns = [
            '.tmp', '.temp', '.lock', '.crdownload', '.part',
            'thumbs.db', 'desktop.ini', '.ds_store'
        ]
        
        # Check filename patterns
        filename_lower = file_path_obj.name.lower()
        for pattern in ignore_patterns:
            if pattern in filename_lower:
                return True
        
        # Ignore files starting with dot (hidden files)
        if file_path_obj.name.startswith('.'):
            return True
        
        return False
    
    def _handle_file_created(self, file_path: str):
        """Handle new file creation."""
        try:
            # Classify the file
            classification = self.classifier.classify_file(file_path)
            
            # Organize the file (move/rename if needed)
            organized_path = self.organizer.organize_file(file_path, classification)
            
            # Add to inventory
            self.db_manager.add_file(
                organized_path,
                label=classification['label'],
                tags=classification['tags'],
                mime_type=classification['mime_type'],
                metadata=classification.get('metadata', {})
            )
            
            logger.info(f"File processed successfully: {file_path} -> {organized_path}")
            
        except Exception as e:
            logger.error(f"Error handling file creation {file_path}: {e}")
    
    def _handle_file_moved(self, old_path: str, new_path: str):
        """Handle file move events."""
        try:
            # Update database with new location
            self.db_manager.update_file_location(old_path, new_path)
            logger.info(f"File move tracked: {old_path} -> {new_path}")
            
        except Exception as e:
            logger.error(f"Error handling file move {old_path} -> {new_path}: {e}")

class FileWatcher:
    """File system watcher service."""
    
    def __init__(self, db_manager, config_manager):
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.observer = Observer()
        self.event_handler = FileWatcherHandler(db_manager, config_manager)
        self._running = False
    
    def start(self):
        """Start file watching."""
        try:
            if self._running:
                logger.warning("File watcher is already running")
                return
            
            watch_paths = self.config_manager.get_watch_paths()
            
            for path in watch_paths:
                if os.path.exists(path):
                    self.observer.schedule(
                        self.event_handler,
                        path,
                        recursive=True
                    )
                    logger.info(f"Watching path: {path}")
                else:
                    logger.warning(f"Watch path does not exist: {path}")
            
            self.observer.start()
            self._running = True
            logger.info("File watcher started successfully")
            
        except Exception as e:
            logger.error(f"Error starting file watcher: {e}")
            raise
    
    def stop(self):
        """Stop file watching."""
        try:
            if not self._running:
                logger.warning("File watcher is not running")
                return
            
            self.observer.stop()
            self.observer.join()
            self._running = False
            logger.info("File watcher stopped")
            
        except Exception as e:
            logger.error(f"Error stopping file watcher: {e}")
    
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running and self.observer.is_alive()
