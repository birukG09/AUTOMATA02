import os
import mimetypes
import re
from pathlib import Path
from typing import Dict, List, Any
from utils.logger import setup_logger

logger = setup_logger()

class FileClassifier:
    """Rule-based file classifier."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        
        # Initialize mimetypes
        mimetypes.init()
    
    def classify_file(self, file_path: str) -> Dict[str, Any]:
        """Classify file using rules and return classification info."""
        try:
            file_path_obj = Path(file_path)
            
            # Get basic file info
            mime_type, _ = mimetypes.guess_type(str(file_path_obj))
            if not mime_type:
                mime_type = self._guess_mime_from_extension(file_path_obj.suffix.lower())
            
            # Get file stats
            stat = file_path_obj.stat()
            
            # Base classification
            classification = {
                'label': 'other',
                'tags': [],
                'mime_type': mime_type,
                'confidence': 0.0,
                'metadata': {
                    'filename': file_path_obj.name,
                    'extension': file_path_obj.suffix.lower(),
                    'size_bytes': stat.st_size
                }
            }
            
            # Apply rules
            rules = self.config_manager.get_rules()
            matched_rule = self._apply_rules(file_path_obj, mime_type, stat, rules)
            
            if matched_rule:
                classification.update(matched_rule)
                classification['confidence'] = 0.9
            else:
                # Fallback classification
                fallback = self._fallback_classification(file_path_obj, mime_type)
                classification['label'] = fallback['label']
                classification['tags'] = fallback['tags']
                classification['confidence'] = 0.5
            
            logger.debug(f"File classified: {file_path_obj} -> {classification['label']}")
            return classification
            
        except Exception as e:
            logger.error(f"Error classifying file {file_path}: {e}")
            return {
                'label': 'other',
                'tags': [],
                'mime_type': mime_type or 'application/octet-stream',
                'confidence': 0.0,
                'metadata': {}
            }
    
    def _apply_rules(self, file_path: Path, mime_type: str, stat: os.stat_result, 
                     rules: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        """Apply classification rules to file."""
        # Sort rules by priority (lower number = higher priority)
        sorted_rules = sorted(rules, key=lambda x: x.get('priority', 100))
        
        for rule in sorted_rules:
            if not rule.get('active', True):
                continue
            
            if self._rule_matches(file_path, mime_type or '', stat, rule):
                logger.debug(f"Rule matched: {rule['name']} for {file_path}")
                return self._apply_rule_actions(rule)
        
        return None
    
    def _rule_matches(self, file_path: Path, mime_type: str, stat: os.stat_result, 
                      rule: Dict[str, Any]) -> bool:
        """Check if rule conditions match the file."""
        conditions = rule.get('when', {})
        
        # Filename regex
        if 'filename_regex' in conditions:
            pattern = conditions['filename_regex']
            if not re.search(pattern, file_path.name, re.IGNORECASE):
                return False
        
        # MIME type conditions
        if 'mime_in' in conditions:
            if mime_type not in conditions['mime_in']:
                return False
        
        if 'mime_startswith' in conditions:
            if not mime_type or not mime_type.startswith(conditions['mime_startswith']):
                return False
        
        # Path regex
        if 'path_regex' in conditions:
            pattern = conditions['path_regex']
            if not re.search(pattern, str(file_path), re.IGNORECASE):
                return False
        
        # Size conditions
        if 'size_lt_bytes' in conditions:
            if stat.st_size >= conditions['size_lt_bytes']:
                return False
        
        if 'size_gt_bytes' in conditions:
            if stat.st_size <= conditions['size_gt_bytes']:
                return False
        
        return True
    
    def _apply_rule_actions(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply rule actions and return classification."""
        actions = rule.get('then', {})
        
        return {
            'label': actions.get('label', 'other'),
            'tags': actions.get('tags_add', []),
            'rule_matched': rule['name'],
            'move_to': actions.get('move_to'),
            'rename_to': actions.get('rename_to')
        }
    
    def _fallback_classification(self, file_path: Path, mime_type: str) -> Dict[str, Any]:
        """Fallback classification based on common patterns."""
        filename_lower = file_path.name.lower()
        extension = file_path.suffix.lower()
        
        # Financial documents
        finance_patterns = [
            'invoice', 'bill', 'statement', 'receipt', 'transaction',
            'bank', 'credit', 'debit', 'payment', 'expense'
        ]
        for pattern in finance_patterns:
            if pattern in filename_lower:
                return {'label': 'finance', 'tags': ['auto-classified']}
        
        # Media files
        if mime_type and mime_type.startswith('image/'):
            return {'label': 'media', 'tags': ['image', 'auto-classified']}
        
        if mime_type and mime_type.startswith('video/'):
            return {'label': 'media', 'tags': ['video', 'auto-classified']}
        
        if mime_type and mime_type.startswith('audio/'):
            return {'label': 'media', 'tags': ['audio', 'auto-classified']}
        
        # Documents
        document_types = ['.pdf', '.doc', '.docx', '.txt', '.rtf']
        if extension in document_types:
            return {'label': 'documents', 'tags': ['document', 'auto-classified']}
        
        # Code files
        code_extensions = [
            '.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h',
            '.php', '.rb', '.go', '.rs', '.swift', '.kt'
        ]
        if extension in code_extensions:
            return {'label': 'code', 'tags': ['source-code', 'auto-classified']}
        
        # Archives
        archive_extensions = ['.zip', '.rar', '.tar', '.gz', '.7z']
        if extension in archive_extensions:
            return {'label': 'archives', 'tags': ['archive', 'auto-classified']}
        
        return {'label': 'other', 'tags': ['unclassified']}
    
    def _guess_mime_from_extension(self, extension: str) -> str:
        """Guess MIME type from file extension."""
        mime_map = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.txt': 'text/plain',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.mp4': 'video/mp4',
            '.avi': 'video/avi',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.zip': 'application/zip',
            '.py': 'text/x-python'
        }
        
        return mime_map.get(extension, 'application/octet-stream')
