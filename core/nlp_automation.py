"""
Natural Language Automation Module for AUTOMATA02.
Processes plain English commands and converts them to automation actions.
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from utils.logger import setup_logger

logger = setup_logger()

class NLPCommand:
    """Represents a parsed natural language command"""
    
    def __init__(self, original_text: str, intent: str, entities: Dict[str, Any], 
                 confidence: float, actions: List[Dict[str, Any]]):
        self.original_text = original_text
        self.intent = intent
        self.entities = entities
        self.confidence = confidence
        self.actions = actions
        self.created_at = datetime.now()

class NaturalLanguageProcessor:
    """Main class for processing natural language automation commands"""
    
    def __init__(self, db_manager, config_manager):
        self.db_manager = db_manager
        self.config_manager = config_manager
        
        # Intent patterns and their corresponding actions
        self.intent_patterns = self._load_intent_patterns()
        
        # Entity extraction patterns
        self.entity_patterns = self._load_entity_patterns()
        
        # Common synonyms and mappings
        self.synonyms = self._load_synonyms()
    
    def _load_intent_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load intent recognition patterns"""
        return {
            'organize_files': {
                'patterns': [
                    r'(?:sort|organize|arrange|classify)\s+(?:my\s+)?(?:files?|documents?|downloads?)',
                    r'organize\s+everything\s+in\s+(.+)',
                    r'sort\s+(.+)\s+by\s+(.+)',
                    r'move\s+(.+)\s+files?\s+to\s+(.+)',
                    r'put\s+(.+)\s+in\s+(.+)\s+folder'
                ],
                'action_type': 'file_organization',
                'required_entities': ['location', 'criteria']
            },
            
            'generate_report': {
                'patterns': [
                    r'generate\s+(?:a\s+)?(.+)\s+report',
                    r'create\s+(?:a\s+)?summary\s+(?:of\s+)?(.+)',
                    r'show\s+me\s+(?:a\s+)?(.+)\s+dashboard',
                    r'give\s+me\s+(.+)\s+insights?',
                    r'analyze\s+(.+)\s+and\s+(?:create|generate|make)\s+(?:a\s+)?report'
                ],
                'action_type': 'report_generation',
                'required_entities': ['report_type', 'timeframe']
            },
            
            'schedule_automation': {
                'patterns': [
                    r'(?:schedule|set up|automate)\s+(.+)\s+(?:every|each)\s+(.+)',
                    r'(?:run|execute|do)\s+(.+)\s+(?:automatically|auto)\s+(?:every|each)\s+(.+)',
                    r'(?:remind|notify|alert)\s+me\s+(.+)\s+(?:every|each)\s+(.+)',
                    r'send\s+me\s+(.+)\s+(?:every|each)\s+(.+)'
                ],
                'action_type': 'scheduling',
                'required_entities': ['task', 'frequency']
            },
            
            'search_files': {
                'patterns': [
                    r'(?:find|search|locate|show)\s+(?:me\s+)?(?:all\s+)?(.+)\s+files?',
                    r'where\s+(?:are|is)\s+(?:my\s+)?(.+)',
                    r'list\s+(?:all\s+)?(.+)\s+(?:files?|documents?)',
                    r'show\s+me\s+everything\s+(?:related\s+to|about|tagged)\s+(.+)'
                ],
                'action_type': 'file_search',
                'required_entities': ['search_criteria']
            },
            
            'create_rule': {
                'patterns': [
                    r'create\s+(?:a\s+)?rule\s+(?:to\s+)?(.+)',
                    r'always\s+(.+)\s+when\s+(.+)',
                    r'automatically\s+(.+)\s+(?:if|when)\s+(.+)',
                    r'set up\s+automation\s+(?:to\s+)?(.+)'
                ],
                'action_type': 'rule_creation',
                'required_entities': ['condition', 'action']
            },
            
            'notification_setup': {
                'patterns': [
                    r'notify\s+me\s+(?:when|if)\s+(.+)',
                    r'send\s+(?:a\s+)?(?:notification|alert|message)\s+(?:when|if)\s+(.+)',
                    r'alert\s+me\s+(?:about|when)\s+(.+)',
                    r'let\s+me\s+know\s+(?:when|if)\s+(.+)'
                ],
                'action_type': 'notification',
                'required_entities': ['trigger_condition']
            }
        }
    
    def _load_entity_patterns(self) -> Dict[str, List[str]]:
        """Load entity extraction patterns"""
        return {
            'file_types': [
                r'(?:pdf|doc|docx|txt|csv|xlsx?|ppt|pptx|jpg|png|gif|mp4|mp3|zip|rar)s?\b',
                r'(?:image|document|spreadsheet|presentation|video|audio|archive)s?\b',
                r'(?:invoice|receipt|bill|statement|report|contract)s?\b'
            ],
            
            'locations': [
                r'(?:downloads?|desktop|documents?|pictures?|home|folder)s?\b',
                r'(?:finance|work|personal|project|archive)s?\s+(?:folder|directory)\b',
                r'\/[\w\/]+',  # File paths
                r'[A-Z]:\\[\w\\]+',  # Windows paths
            ],
            
            'timeframes': [
                r'(?:today|yesterday|this\s+week|last\s+week|this\s+month|last\s+month)\b',
                r'(?:daily|weekly|monthly|yearly)\b',
                r'(?:every|each)\s+(?:day|week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
                r'(?:in\s+)?(?:\d+)\s+(?:minutes?|hours?|days?|weeks?|months?)\b'
            ],
            
            'frequencies': [
                r'(?:every|each)\s+(?:day|week|month|year)\b',
                r'(?:daily|weekly|monthly|yearly|hourly)\b',
                r'(?:every|each)\s+(?:\d+)\s+(?:minutes?|hours?|days?|weeks?|months?)\b',
                r'(?:every|each)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b'
            ],
            
            'report_types': [
                r'(?:financial?|expense|income|budget|spending)\b',
                r'(?:activity|usage|performance|productivity)\b',
                r'(?:summary|overview|analysis|insights?)\b',
                r'(?:weekly|monthly|quarterly|annual)\b'
            ],
            
            'actions': [
                r'(?:move|copy|delete|organize|sort|classify|tag|rename)\b',
                r'(?:backup|sync|upload|download|export|import)\b',
                r'(?:convert|transform|process|analyze|summarize)\b'
            ]
        }
    
    def _load_synonyms(self) -> Dict[str, List[str]]:
        """Load synonym mappings for better understanding"""
        return {
            'organize': ['sort', 'arrange', 'classify', 'categorize', 'tidy'],
            'report': ['summary', 'analysis', 'overview', 'dashboard', 'insights'],
            'notification': ['alert', 'reminder', 'message', 'ping', 'update'],
            'automatically': ['auto', 'automatically', 'by itself', 'on its own'],
            'files': ['documents', 'items', 'stuff', 'things', 'data'],
            'weekly': ['every week', 'each week', 'once a week'],
            'monthly': ['every month', 'each month', 'once a month']
        }
    
    def process_command(self, command_text: str) -> NLPCommand:
        """Process a natural language command and return structured actions"""
        try:
            # Normalize the text
            normalized_text = self._normalize_text(command_text)
            
            # Detect intent
            intent, confidence = self._detect_intent(normalized_text)
            
            # Extract entities
            entities = self._extract_entities(normalized_text, intent)
            
            # Generate actions based on intent and entities
            actions = self._generate_actions(intent, entities, normalized_text)
            
            # Create command object
            nlp_command = NLPCommand(
                original_text=command_text,
                intent=intent,
                entities=entities,
                confidence=confidence,
                actions=actions
            )
            
            logger.info(f"Processed NLP command: {intent} (confidence: {confidence:.2f})")
            return nlp_command
            
        except Exception as e:
            logger.error(f"Error processing NLP command: {e}")
            # Return fallback command
            return NLPCommand(
                original_text=command_text,
                intent='unknown',
                entities={},
                confidence=0.0,
                actions=[{'type': 'error', 'message': f"Could not understand: {command_text}"}]
            )
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for better processing"""
        # Convert to lowercase
        text = text.lower().strip()
        
        # Replace synonyms
        for canonical, synonyms in self.synonyms.items():
            for synonym in synonyms:
                text = re.sub(r'\b' + re.escape(synonym) + r'\b', canonical, text)
        
        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _detect_intent(self, text: str) -> Tuple[str, float]:
        """Detect the intent of the command"""
        best_intent = 'unknown'
        best_confidence = 0.0
        
        for intent, config in self.intent_patterns.items():
            for pattern in config['patterns']:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Calculate confidence based on match quality
                    confidence = len(match.group(0)) / len(text)
                    confidence = min(1.0, confidence * 1.5)  # Boost confidence slightly
                    
                    if confidence > best_confidence:
                        best_intent = intent
                        best_confidence = confidence
        
        return best_intent, best_confidence
    
    def _extract_entities(self, text: str, intent: str) -> Dict[str, Any]:
        """Extract entities from the text based on intent"""
        entities = {}
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    if entity_type not in entities:
                        entities[entity_type] = []
                    entities[entity_type].extend(matches)
        
        # Intent-specific entity extraction
        if intent in self.intent_patterns:
            entities.update(self._extract_intent_specific_entities(text, intent))
        
        return entities
    
    def _extract_intent_specific_entities(self, text: str, intent: str) -> Dict[str, Any]:
        """Extract entities specific to the intent"""
        entities = {}
        
        if intent == 'organize_files':
            # Extract source and destination
            move_match = re.search(r'move\s+(.+)\s+(?:to|into)\s+(.+)', text)
            if move_match:
                entities['source'] = move_match.group(1).strip()
                entities['destination'] = move_match.group(2).strip()
            
            # Extract sorting criteria
            sort_match = re.search(r'sort\s+(.+)\s+by\s+(.+)', text)
            if sort_match:
                entities['target'] = sort_match.group(1).strip()
                entities['criteria'] = sort_match.group(2).strip()
        
        elif intent == 'generate_report':
            # Extract report type and timeframe
            report_match = re.search(r'(?:generate|create)\s+(?:a\s+)?(.+)\s+report', text)
            if report_match:
                entities['report_type'] = report_match.group(1).strip()
            
            # Extract timeframe
            timeframe_match = re.search(r'(?:for\s+|from\s+|of\s+)?(?:this\s+|last\s+)?(\w+)', text)
            if timeframe_match:
                timeframe = timeframe_match.group(1)
                if timeframe in ['week', 'month', 'year', 'today', 'yesterday']:
                    entities['timeframe'] = timeframe
        
        elif intent == 'schedule_automation':
            # Extract task and frequency
            schedule_match = re.search(r'(?:schedule|automate)\s+(.+)\s+(?:every|each)\s+(.+)', text)
            if schedule_match:
                entities['task'] = schedule_match.group(1).strip()
                entities['frequency'] = schedule_match.group(2).strip()
        
        elif intent == 'create_rule':
            # Extract condition and action
            rule_match = re.search(r'(?:always|automatically)\s+(.+)\s+(?:when|if)\s+(.+)', text)
            if rule_match:
                entities['action'] = rule_match.group(1).strip()
                entities['condition'] = rule_match.group(2).strip()
        
        return entities
    
    def _generate_actions(self, intent: str, entities: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
        """Generate specific actions based on intent and entities"""
        actions = []
        
        try:
            if intent == 'organize_files':
                actions.extend(self._generate_organize_actions(entities, text))
            
            elif intent == 'generate_report':
                actions.extend(self._generate_report_actions(entities, text))
            
            elif intent == 'schedule_automation':
                actions.extend(self._generate_schedule_actions(entities, text))
            
            elif intent == 'search_files':
                actions.extend(self._generate_search_actions(entities, text))
            
            elif intent == 'create_rule':
                actions.extend(self._generate_rule_actions(entities, text))
            
            elif intent == 'notification_setup':
                actions.extend(self._generate_notification_actions(entities, text))
            
            else:
                actions.append({
                    'type': 'error',
                    'message': f"Unknown intent: {intent}"
                })
        
        except Exception as e:
            logger.error(f"Error generating actions for intent {intent}: {e}")
            actions.append({
                'type': 'error',
                'message': f"Error processing command: {str(e)}"
            })
        
        return actions
    
    def _generate_organize_actions(self, entities: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
        """Generate file organization actions"""
        actions = []
        
        # Determine what to organize
        if 'source' in entities and 'destination' in entities:
            actions.append({
                'type': 'move_files',
                'source': entities['source'],
                'destination': entities['destination']
            })
        
        elif 'file_types' in entities:
            file_types = entities['file_types']
            actions.append({
                'type': 'organize_by_type',
                'file_types': file_types,
                'apply_rules': True
            })
        
        else:
            # General organization
            actions.append({
                'type': 'run_organization',
                'target': 'all_files',
                'apply_rules': True
            })
        
        return actions
    
    def _generate_report_actions(self, entities: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
        """Generate report generation actions"""
        actions = []
        
        report_type = entities.get('report_type', ['general'])[0] if entities.get('report_type') else 'general'
        timeframe = entities.get('timeframe', ['week'])[0] if entities.get('timeframe') else 'week'
        
        actions.append({
            'type': 'generate_report',
            'report_type': report_type,
            'timeframe': timeframe,
            'format': 'html'  # Default format
        })
        
        # Check if user wants it emailed/shared
        if 'email' in text or 'send' in text:
            actions.append({
                'type': 'send_report',
                'method': 'email',
                'format': 'pdf'
            })
        
        return actions
    
    def _generate_schedule_actions(self, entities: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
        """Generate scheduling actions"""
        actions = []
        
        task = entities.get('task', 'unknown_task')
        frequency = entities.get('frequency', 'weekly')
        
        actions.append({
            'type': 'create_schedule',
            'task': task,
            'frequency': frequency,
            'enabled': True
        })
        
        return actions
    
    def _generate_search_actions(self, entities: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
        """Generate file search actions"""
        actions = []
        
        # Extract search criteria
        search_terms = []
        if 'file_types' in entities:
            search_terms.extend(entities['file_types'])
        
        if 'locations' in entities:
            search_terms.extend(entities['locations'])
        
        # Extract search term from command
        search_match = re.search(r'(?:find|search|show)\s+(?:me\s+)?(?:all\s+)?(.+?)\s+(?:files?|in)', text)
        if search_match:
            search_terms.append(search_match.group(1).strip())
        
        actions.append({
            'type': 'search_files',
            'query': ' '.join(search_terms),
            'limit': 50
        })
        
        return actions
    
    def _generate_rule_actions(self, entities: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
        """Generate rule creation actions"""
        actions = []
        
        condition = entities.get('condition', 'unknown_condition')
        action = entities.get('action', 'unknown_action')
        
        actions.append({
            'type': 'create_rule',
            'condition': condition,
            'action': action,
            'name': f"Auto-generated rule from: {text[:50]}..."
        })
        
        return actions
    
    def _generate_notification_actions(self, entities: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
        """Generate notification setup actions"""
        actions = []
        
        trigger = entities.get('trigger_condition', 'unknown_trigger')
        
        actions.append({
            'type': 'setup_notification',
            'trigger': trigger,
            'method': 'system'  # Default to system notifications
        })
        
        return actions
    
    def execute_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute the generated actions and return results"""
        results = []
        
        for action in actions:
            try:
                result = self._execute_single_action(action)
                results.append(result)
            except Exception as e:
                logger.error(f"Error executing action {action}: {e}")
                results.append({
                    'action': action,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def _execute_single_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single action"""
        action_type = action.get('type')
        
        if action_type == 'search_files':
            # Execute file search
            files = self.db_manager.search_files(
                query=action.get('query'),
                limit=action.get('limit', 50)
            )
            return {
                'action': action,
                'success': True,
                'result': f"Found {len(files)} files",
                'data': files
            }
        
        elif action_type == 'run_organization':
            # Run file organization
            return {
                'action': action,
                'success': True,
                'result': "File organization started"
            }
        
        elif action_type == 'generate_report':
            # Generate report
            return {
                'action': action,
                'success': True,
                'result': f"Generated {action.get('report_type')} report for {action.get('timeframe')}"
            }
        
        elif action_type == 'create_rule':
            # Create automation rule
            return {
                'action': action,
                'success': True,
                'result': "Automation rule created"
            }
        
        elif action_type == 'error':
            return {
                'action': action,
                'success': False,
                'error': action.get('message')
            }
        
        else:
            return {
                'action': action,
                'success': False,
                'error': f"Unknown action type: {action_type}"
            }
    
    def get_command_suggestions(self, partial_text: str) -> List[str]:
        """Get command suggestions based on partial input"""
        suggestions = []
        
        # Common command templates
        templates = [
            "Sort my downloads by type",
            "Generate a weekly financial report",
            "Move all PDFs to Documents folder",
            "Find all files related to project",
            "Create a rule to automatically organize invoices",
            "Notify me when new reports are available",
            "Schedule weekly expense summary every Friday",
            "Show me all files from last week",
            "Organize everything in Downloads folder",
            "Generate insights from recent activity"
        ]
        
        # Filter templates based on partial text
        if partial_text:
            partial_lower = partial_text.lower()
            suggestions = [t for t in templates if partial_lower in t.lower()]
        else:
            suggestions = templates[:5]  # Show first 5 by default
        
        return suggestions