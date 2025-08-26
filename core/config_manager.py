import json
import yaml
import os
from pathlib import Path
from typing import Dict, List, Any
from utils.logger import setup_logger

logger = setup_logger()

class ConfigManager:
    """Manages configuration and rules for file organization."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".automata02"
        self.config_dir.mkdir(exist_ok=True)
        
        self.config_file = self.config_dir / "config.yaml"
        self.rules_file = self.config_dir / "rules.json"
        
        # Initialize config if not exists
        self._init_default_config()
        self._init_default_rules()
    
    def _init_default_config(self):
        """Initialize default configuration."""
        if not self.config_file.exists():
            default_config = {
                'watch_paths': [
                    str(Path.home() / "Downloads")
                ],
                'organize_base_path': str(Path.home() / "AutomataOrganized"),
                'ui_monitor': {
                    'enable': False,
                    'learn_patterns': False
                },
                'report_schedules': ['weekly_sun_18_00'],
                'logging': {
                    'level': 'INFO',
                    'file': str(self.config_dir / "automata02.log")
                }
            }
            
            self._save_yaml_config(default_config)
            logger.info("Default configuration created")
    
    def _init_default_rules(self):
        """Initialize default rules."""
        if not self.rules_file.exists():
            # Load default rules from config/default_rules.json
            default_rules_path = Path(__file__).parent.parent / "config" / "default_rules.json"
            
            if default_rules_path.exists():
                with open(default_rules_path, 'r') as f:
                    default_rules = json.load(f)
            else:
                # Fallback rules if file doesn't exist
                default_rules = self._get_fallback_rules()
            
            self._save_rules(default_rules)
            logger.info("Default rules created")
    
    def _get_fallback_rules(self) -> List[Dict[str, Any]]:
        """Get fallback rules if default rules file is missing."""
        return [
            {
                "name": "PDF Invoices to Finance",
                "priority": 10,
                "active": True,
                "when": {
                    "filename_regex": "invoice|bill|statement|receipt",
                    "mime_in": ["application/pdf"]
                },
                "then": {
                    "label": "finance",
                    "tags_add": ["invoice", "pdf"],
                    "move_to": "{{HOME}}/AutomataOrganized/Finance/{{YYYY}}/{{MM}}"
                }
            },
            {
                "name": "Images to Media",
                "priority": 20,
                "active": True,
                "when": {
                    "mime_startswith": "image/"
                },
                "then": {
                    "label": "media",
                    "tags_add": ["image"],
                    "move_to": "{{HOME}}/AutomataOrganized/Media/Images/{{YYYY}}/{{MM}}"
                }
            },
            {
                "name": "PDF Documents",
                "priority": 30,
                "active": True,
                "when": {
                    "mime_in": ["application/pdf"]
                },
                "then": {
                    "label": "documents",
                    "tags_add": ["pdf", "document"],
                    "move_to": "{{HOME}}/AutomataOrganized/Documents/{{YYYY}}"
                }
            },
            {
                "name": "Code Files",
                "priority": 40,
                "active": True,
                "when": {
                    "filename_regex": r"\.(py|js|html|css|java|cpp|c|h|php|rb|go|rs)$"
                },
                "then": {
                    "label": "code",
                    "tags_add": ["source-code"],
                    "move_to": "{{HOME}}/AutomataOrganized/Code/{{EXT}}"
                }
            }
        ]
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        try:
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def save_config(self, config: Dict[str, Any]):
        """Save configuration."""
        self._save_yaml_config(config)
    
    def _save_yaml_config(self, config: Dict[str, Any]):
        """Save configuration to YAML file."""
        try:
            with open(self.config_file, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False)
            logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def get_watch_paths(self) -> List[str]:
        """Get paths to watch for file changes."""
        config = self.get_config()
        return config.get('watch_paths', [str(Path.home() / "Downloads")])
    
    def set_watch_paths(self, paths: List[str]):
        """Set paths to watch."""
        config = self.get_config()
        config['watch_paths'] = paths
        self.save_config(config)
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all organization rules."""
        try:
            with open(self.rules_file, 'r') as f:
                rules = json.load(f)
                return rules if isinstance(rules, list) else []
        except Exception as e:
            logger.error(f"Error loading rules: {e}")
            return []
    
    def save_rules(self, rules: List[Dict[str, Any]]):
        """Save organization rules."""
        self._save_rules(rules)
    
    def _save_rules(self, rules: List[Dict[str, Any]]):
        """Save rules to JSON file."""
        try:
            with open(self.rules_file, 'w') as f:
                json.dump(rules, f, indent=2)
            logger.info("Rules saved")
        except Exception as e:
            logger.error(f"Error saving rules: {e}")
    
    def add_rule(self, rule: Dict[str, Any]) -> bool:
        """Add a new rule."""
        try:
            rules = self.get_rules()
            rules.append(rule)
            self.save_rules(rules)
            return True
        except Exception as e:
            logger.error(f"Error adding rule: {e}")
            return False
    
    def update_rule(self, index: int, rule: Dict[str, Any]) -> bool:
        """Update existing rule."""
        try:
            rules = self.get_rules()
            if 0 <= index < len(rules):
                rules[index] = rule
                self.save_rules(rules)
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating rule: {e}")
            return False
    
    def delete_rule(self, index: int) -> bool:
        """Delete a rule."""
        try:
            rules = self.get_rules()
            if 0 <= index < len(rules):
                del rules[index]
                self.save_rules(rules)
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting rule: {e}")
            return False
    
    def get_organize_base_path(self) -> str:
        """Get base path for organized files."""
        config = self.get_config()
        return config.get('organize_base_path', str(Path.home() / "AutomataOrganized"))
    
    def set_organize_base_path(self, path: str):
        """Set base path for organized files."""
        config = self.get_config()
        config['organize_base_path'] = path
        self.save_config(config)
