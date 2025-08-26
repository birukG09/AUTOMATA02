import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from utils.logger import setup_logger

logger = setup_logger()

class FileOrganizer:
    """Organizes files based on classification rules."""
    
    def __init__(self, db_manager, config_manager):
        self.db_manager = db_manager
        self.config_manager = config_manager
    
    def organize_file(self, file_path: str, classification: Dict[str, Any]) -> str:
        """Organize file based on classification results."""
        try:
            source_path = Path(file_path)
            
            # Check if file should be moved
            move_to = classification.get('move_to')
            if not move_to:
                # No move rule, keep file in place
                return str(source_path)
            
            # Expand template variables
            destination = self._expand_path_template(move_to, source_path, classification)
            destination_path = Path(destination)
            
            # Create destination directory if it doesn't exist
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle filename conflicts
            final_destination = self._resolve_filename_conflict(destination_path)
            
            # Move the file
            shutil.move(str(source_path), str(final_destination))
            
            logger.info(f"File organized: {source_path} -> {final_destination}")
            
            # Log the move operation
            self.db_manager.log_activity("file_organized", str(source_path), {
                "destination": str(final_destination),
                "label": classification['label'],
                "rule": classification.get('rule_matched', 'fallback')
            })
            
            return str(final_destination)
            
        except Exception as e:
            logger.error(f"Error organizing file {file_path}: {e}")
            self.db_manager.log_activity("file_organize_failed", file_path, {
                "error": str(e)
            }, "error")
            # Return original path if organization fails
            return file_path
    
    def _expand_path_template(self, template: str, source_path: Path, 
                              classification: Dict[str, Any]) -> str:
        """Expand path template with variables."""
        try:
            now = datetime.now()
            
            # Date variables
            template = template.replace('{{YYYY}}', str(now.year))
            template = template.replace('{{MM}}', f"{now.month:02d}")
            template = template.replace('{{DD}}', f"{now.day:02d}")
            template = template.replace('{{HH}}', f"{now.hour:02d}")
            template = template.replace('{{mm}}', f"{now.minute:02d}")
            template = template.replace('{{ss}}', f"{now.second:02d}")
            
            # File variables
            template = template.replace('{{BASENAME}}', source_path.name)
            template = template.replace('{{STEM}}', source_path.stem)
            template = template.replace('{{EXT}}', source_path.suffix)
            
            # Environment variables
            template = template.replace('{{HOME}}', str(Path.home()))
            
            return template
            
        except Exception as e:
            logger.error(f"Error expanding path template: {e}")
            return template
    
    def _resolve_filename_conflict(self, destination_path: Path) -> Path:
        """Resolve filename conflicts by adding counter suffix."""
        if not destination_path.exists():
            return destination_path
        
        stem = destination_path.stem
        suffix = destination_path.suffix
        parent = destination_path.parent
        
        counter = 1
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
            
            # Safety check to avoid infinite loop
            if counter > 1000:
                logger.warning(f"Too many filename conflicts for {destination_path}")
                return destination_path
    
    def create_organized_structure(self, base_path: str | None = None) -> Dict[str, str]:
        """Create organized folder structure."""
        if base_path is None:
            base_path_obj = Path.home() / "AutomataOrganized"
        else:
            base_path_obj = Path(base_path)
        
        # Default folder structure
        folders = {
            'finance': base_path_obj / 'Finance',
            'documents': base_path_obj / 'Documents', 
            'media': base_path_obj / 'Media',
            'code': base_path_obj / 'Code',
            'archives': base_path_obj / 'Archives',
            'other': base_path_obj / 'Other'
        }
        
        # Create folders
        created_folders = {}
        for category, folder_path in folders.items():
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                created_folders[category] = str(folder_path)
                logger.info(f"Created folder: {folder_path}")
            except Exception as e:
                logger.error(f"Error creating folder {folder_path}: {e}")
        
        return created_folders
    
    def dry_run_organize(self, file_path: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """Perform dry run of file organization without actually moving files."""
        try:
            source_path = Path(file_path)
            
            result = {
                'source': str(source_path),
                'would_move': False,
                'destination': None,
                'label': classification['label'],
                'tags': classification['tags'],
                'rule_matched': classification.get('rule_matched', 'fallback')
            }
            
            # Check if file would be moved
            move_to = classification.get('move_to')
            if move_to:
                destination = self._expand_path_template(move_to, source_path, classification)
                destination_path = Path(destination)
                final_destination = self._resolve_filename_conflict(destination_path)
                
                result['would_move'] = True
                result['destination'] = str(final_destination)
                result['destination_exists'] = final_destination.exists()
            
            return result
            
        except Exception as e:
            logger.error(f"Error in dry run for {file_path}: {e}")
            return {
                'source': file_path,
                'error': str(e),
                'would_move': False
            }
