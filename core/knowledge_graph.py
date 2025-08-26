"""
Knowledge Graph Module for AUTOMATA02.
Creates semantic relationships between files, topics, and entities.
"""

import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import networkx as nx
import re
from collections import defaultdict, Counter
from utils.logger import setup_logger

logger = setup_logger()

class Entity:
    """Represents an entity in the knowledge graph"""
    
    def __init__(self, entity_id: str, entity_type: str, name: str, 
                 metadata: Dict[str, Any] = None):
        self.entity_id = entity_id
        self.entity_type = entity_type  # 'file', 'topic', 'person', 'organization', 'project', etc.
        self.name = name
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

class Relationship:
    """Represents a relationship between entities"""
    
    def __init__(self, source_id: str, target_id: str, relationship_type: str,
                 weight: float = 1.0, metadata: Dict[str, Any] = None):
        self.source_id = source_id
        self.target_id = target_id
        self.relationship_type = relationship_type  # 'contains', 'related_to', 'created_by', etc.
        self.weight = weight
        self.metadata = metadata or {}
        self.created_at = datetime.now()

class KnowledgeGraph:
    """Main knowledge graph for semantic file relationships"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.graph = nx.DiGraph()
        
        # Initialize knowledge graph database
        self._init_knowledge_db()
        
        # Entity extractors
        self.entity_extractors = {
            'topics': self._extract_topic_entities,
            'people': self._extract_people_entities,
            'organizations': self._extract_organization_entities,
            'projects': self._extract_project_entities,
            'dates': self._extract_date_entities,
            'locations': self._extract_location_entities
        }
        
        # Load existing graph
        self._load_graph()
    
    def _init_knowledge_db(self):
        """Initialize knowledge graph database tables"""
        try:
            kg_db_path = Path.home() / ".automata02" / "knowledge_graph.sqlite"
            
            with sqlite3.connect(str(kg_db_path)) as conn:
                cursor = conn.cursor()
                
                # Entities table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS entities (
                        entity_id TEXT PRIMARY KEY,
                        entity_type TEXT NOT NULL,
                        name TEXT NOT NULL,
                        metadata TEXT,
                        created_at TEXT,
                        updated_at TEXT
                    )
                ''')
                
                # Relationships table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS relationships (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_id TEXT NOT NULL,
                        target_id TEXT NOT NULL,
                        relationship_type TEXT NOT NULL,
                        weight REAL DEFAULT 1.0,
                        metadata TEXT,
                        created_at TEXT,
                        FOREIGN KEY (source_id) REFERENCES entities (entity_id),
                        FOREIGN KEY (target_id) REFERENCES entities (entity_id)
                    )
                ''')
                
                # Entity mentions table (tracks where entities appear)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS entity_mentions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        entity_id TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        mention_context TEXT,
                        confidence REAL DEFAULT 1.0,
                        created_at TEXT,
                        FOREIGN KEY (entity_id) REFERENCES entities (entity_id)
                    )
                ''')
                
                # Semantic tags table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS semantic_tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL,
                        tag TEXT NOT NULL,
                        tag_type TEXT,
                        confidence REAL DEFAULT 1.0,
                        created_at TEXT
                    )
                ''')
                
                # Create indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_mentions_entity ON entity_mentions(entity_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_mentions_file ON entity_mentions(file_path)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_file ON semantic_tags(file_path)')
                
                conn.commit()
                logger.info("Knowledge graph database initialized")
                
        except Exception as e:
            logger.error(f"Error initializing knowledge graph database: {e}")
    
    def add_file_to_graph(self, file_path: str, content: str = None, 
                         metadata: Dict[str, Any] = None) -> str:
        """Add a file to the knowledge graph and extract entities"""
        try:
            # Create file entity
            file_id = self._generate_entity_id(file_path)
            file_entity = Entity(
                entity_id=file_id,
                entity_type='file',
                name=Path(file_path).name,
                metadata={
                    'path': file_path,
                    'extension': Path(file_path).suffix.lower(),
                    **(metadata or {})
                }
            )
            
            self._save_entity(file_entity)
            self.graph.add_node(file_id, **file_entity.__dict__)
            
            # Extract entities from file content if available
            if content:
                extracted_entities = self._extract_entities_from_content(content, file_path)
                
                # Create relationships between file and extracted entities
                for entity in extracted_entities:
                    self._save_entity(entity)
                    self.graph.add_node(entity.entity_id, **entity.__dict__)
                    
                    # Create relationship
                    relationship = Relationship(
                        source_id=file_id,
                        target_id=entity.entity_id,
                        relationship_type='contains',
                        weight=1.0
                    )
                    self._save_relationship(relationship)
                    self.graph.add_edge(file_id, entity.entity_id, **relationship.__dict__)
            
            # Extract semantic tags
            semantic_tags = self._extract_semantic_tags(file_path, content)
            for tag, tag_type, confidence in semantic_tags:
                self._save_semantic_tag(file_path, tag, tag_type, confidence)
            
            logger.debug(f"Added file to knowledge graph: {file_path}")
            return file_id
            
        except Exception as e:
            logger.error(f"Error adding file to knowledge graph: {e}")
            return ""
    
    def _generate_entity_id(self, identifier: str) -> str:
        """Generate unique entity ID"""
        return hashlib.md5(identifier.encode()).hexdigest()
    
    def _extract_entities_from_content(self, content: str, file_path: str) -> List[Entity]:
        """Extract entities from file content"""
        entities = []
        
        try:
            for extractor_name, extractor_func in self.entity_extractors.items():
                extracted = extractor_func(content, file_path)
                entities.extend(extracted)
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities from content: {e}")
            return []
    
    def _extract_topic_entities(self, content: str, file_path: str) -> List[Entity]:
        """Extract topic entities from content"""
        entities = []
        
        # Simple keyword-based topic extraction
        topics = {
            'finance': ['invoice', 'payment', 'bill', 'expense', 'budget', 'tax', 'financial'],
            'technology': ['software', 'programming', 'code', 'api', 'database', 'algorithm'],
            'business': ['meeting', 'proposal', 'contract', 'strategy', 'marketing', 'sales'],
            'research': ['study', 'analysis', 'data', 'report', 'findings', 'methodology'],
            'legal': ['contract', 'agreement', 'legal', 'law', 'compliance', 'regulation'],
            'education': ['course', 'lesson', 'tutorial', 'learning', 'education', 'training']
        }
        
        content_lower = content.lower()
        
        for topic, keywords in topics.items():
            matches = sum(1 for keyword in keywords if keyword in content_lower)
            if matches >= 2:  # Require at least 2 keyword matches
                entity_id = self._generate_entity_id(f"topic:{topic}")
                entity = Entity(
                    entity_id=entity_id,
                    entity_type='topic',
                    name=topic,
                    metadata={
                        'keyword_matches': matches,
                        'keywords_found': [kw for kw in keywords if kw in content_lower]
                    }
                )
                entities.append(entity)
                
                # Save entity mention
                self._save_entity_mention(entity_id, file_path, f"Topic: {topic}", matches / len(keywords))
        
        return entities
    
    def _extract_people_entities(self, content: str, file_path: str) -> List[Entity]:
        """Extract people entities from content"""
        entities = []
        
        # Simple name pattern matching
        name_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
            r'\b[A-Z]\. [A-Z][a-z]+\b',      # F. Last
            r'\b[A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+\b'  # First M. Last
        ]
        
        found_names = set()
        for pattern in name_patterns:
            matches = re.findall(pattern, content)
            found_names.update(matches)
        
        for name in found_names:
            if self._is_likely_person_name(name):
                entity_id = self._generate_entity_id(f"person:{name}")
                entity = Entity(
                    entity_id=entity_id,
                    entity_type='person',
                    name=name,
                    metadata={'confidence': 0.8}
                )
                entities.append(entity)
                
                # Save entity mention
                self._save_entity_mention(entity_id, file_path, f"Person: {name}", 0.8)
        
        return entities
    
    def _extract_organization_entities(self, content: str, file_path: str) -> List[Entity]:
        """Extract organization entities from content"""
        entities = []
        
        # Organization patterns
        org_patterns = [
            r'\b[A-Z][a-z]+ (?:Inc|Corp|LLC|Ltd|Company|Corporation|Organization)\b',
            r'\b[A-Z]+ [A-Z]+\b',  # Acronyms
            r'\b[A-Z][a-zA-Z]* (?:University|College|Institute|Foundation)\b'
        ]
        
        found_orgs = set()
        for pattern in org_patterns:
            matches = re.findall(pattern, content)
            found_orgs.update(matches)
        
        for org in found_orgs:
            entity_id = self._generate_entity_id(f"organization:{org}")
            entity = Entity(
                entity_id=entity_id,
                entity_type='organization',
                name=org,
                metadata={'confidence': 0.7}
            )
            entities.append(entity)
            
            # Save entity mention
            self._save_entity_mention(entity_id, file_path, f"Organization: {org}", 0.7)
        
        return entities
    
    def _extract_project_entities(self, content: str, file_path: str) -> List[Entity]:
        """Extract project entities from content"""
        entities = []
        
        # Project indicators
        project_patterns = [
            r'[Pp]roject\s+([A-Z][a-zA-Z\s]+)',
            r'([A-Z][a-zA-Z]+)\s+[Pp]roject',
            r'#([a-zA-Z0-9_-]+)',  # Hashtag-style project names
        ]
        
        found_projects = set()
        for pattern in project_patterns:
            matches = re.findall(pattern, content)
            found_projects.update(matches)
        
        for project in found_projects:
            if len(project.strip()) > 2:  # Filter out very short matches
                entity_id = self._generate_entity_id(f"project:{project}")
                entity = Entity(
                    entity_id=entity_id,
                    entity_type='project',
                    name=project.strip(),
                    metadata={'confidence': 0.6}
                )
                entities.append(entity)
                
                # Save entity mention
                self._save_entity_mention(entity_id, file_path, f"Project: {project}", 0.6)
        
        return entities
    
    def _extract_date_entities(self, content: str, file_path: str) -> List[Entity]:
        """Extract date entities from content"""
        entities = []
        
        # Date patterns
        date_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # MM/DD/YYYY
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
        ]
        
        found_dates = set()
        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            found_dates.update(matches)
        
        for date in found_dates:
            entity_id = self._generate_entity_id(f"date:{date}")
            entity = Entity(
                entity_id=entity_id,
                entity_type='date',
                name=date,
                metadata={'confidence': 0.9}
            )
            entities.append(entity)
            
            # Save entity mention
            self._save_entity_mention(entity_id, file_path, f"Date: {date}", 0.9)
        
        return entities
    
    def _extract_location_entities(self, content: str, file_path: str) -> List[Entity]:
        """Extract location entities from content"""
        entities = []
        
        # Simple location patterns (this could be enhanced with NLP)
        location_indicators = [
            'Street', 'Avenue', 'Road', 'Drive', 'Boulevard',
            'City', 'State', 'Country', 'County',
            'Building', 'Office', 'Floor'
        ]
        
        # Look for patterns like "123 Main Street" or "New York City"
        location_patterns = [
            r'\b\d+\s+[A-Z][a-z]+\s+(?:Street|Avenue|Road|Drive|Boulevard)\b',
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+(?:City|County|State)\b'
        ]
        
        found_locations = set()
        for pattern in location_patterns:
            matches = re.findall(pattern, content)
            found_locations.update(matches)
        
        for location in found_locations:
            entity_id = self._generate_entity_id(f"location:{location}")
            entity = Entity(
                entity_id=entity_id,
                entity_type='location',
                name=location,
                metadata={'confidence': 0.5}
            )
            entities.append(entity)
            
            # Save entity mention
            self._save_entity_mention(entity_id, file_path, f"Location: {location}", 0.5)
        
        return entities
    
    def _extract_semantic_tags(self, file_path: str, content: str = None) -> List[Tuple[str, str, float]]:
        """Extract semantic tags from file"""
        tags = []
        
        try:
            file_path_obj = Path(file_path)
            
            # File type tags
            ext = file_path_obj.suffix.lower()
            if ext:
                tags.append((ext.lstrip('.'), 'file_type', 1.0))
            
            # Directory-based tags
            parts = file_path_obj.parts
            for part in parts:
                if part.lower() in ['finance', 'work', 'personal', 'project', 'temp', 'archive']:
                    tags.append((part.lower(), 'category', 0.8))
            
            # Content-based tags
            if content:
                content_lower = content.lower()
                
                # Technical tags
                if any(word in content_lower for word in ['function', 'class', 'import', 'def']):
                    tags.append(('programming', 'technical', 0.9))
                
                if any(word in content_lower for word in ['select', 'insert', 'update', 'database']):
                    tags.append(('database', 'technical', 0.9))
                
                # Business tags
                if any(word in content_lower for word in ['meeting', 'agenda', 'action items']):
                    tags.append(('meeting', 'business', 0.8))
                
                if any(word in content_lower for word in ['contract', 'agreement', 'terms']):
                    tags.append(('legal', 'business', 0.8))
            
            return tags
            
        except Exception as e:
            logger.error(f"Error extracting semantic tags: {e}")
            return []
    
    def _is_likely_person_name(self, name: str) -> bool:
        """Check if a string is likely a person's name"""
        # Simple heuristics
        parts = name.split()
        if len(parts) < 2:
            return False
        
        # Check if it's not likely to be a place or organization
        non_name_indicators = ['Inc', 'Corp', 'LLC', 'Ltd', 'Avenue', 'Street', 'City', 'State']
        if any(indicator in name for indicator in non_name_indicators):
            return False
        
        return True
    
    def _save_entity(self, entity: Entity):
        """Save entity to database"""
        try:
            kg_db_path = Path.home() / ".automata02" / "knowledge_graph.sqlite"
            with sqlite3.connect(str(kg_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO entities
                    (entity_id, entity_type, name, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    entity.entity_id,
                    entity.entity_type,
                    entity.name,
                    json.dumps(entity.metadata),
                    entity.created_at.isoformat(),
                    entity.updated_at.isoformat()
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving entity: {e}")
    
    def _save_relationship(self, relationship: Relationship):
        """Save relationship to database"""
        try:
            kg_db_path = Path.home() / ".automata02" / "knowledge_graph.sqlite"
            with sqlite3.connect(str(kg_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO relationships
                    (source_id, target_id, relationship_type, weight, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    relationship.source_id,
                    relationship.target_id,
                    relationship.relationship_type,
                    relationship.weight,
                    json.dumps(relationship.metadata),
                    relationship.created_at.isoformat()
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving relationship: {e}")
    
    def _save_entity_mention(self, entity_id: str, file_path: str, context: str, confidence: float):
        """Save entity mention to database"""
        try:
            kg_db_path = Path.home() / ".automata02" / "knowledge_graph.sqlite"
            with sqlite3.connect(str(kg_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO entity_mentions
                    (entity_id, file_path, mention_context, confidence, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    entity_id,
                    file_path,
                    context,
                    confidence,
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving entity mention: {e}")
    
    def _save_semantic_tag(self, file_path: str, tag: str, tag_type: str, confidence: float):
        """Save semantic tag to database"""
        try:
            kg_db_path = Path.home() / ".automata02" / "knowledge_graph.sqlite"
            with sqlite3.connect(str(kg_db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO semantic_tags
                    (file_path, tag, tag_type, confidence, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    file_path,
                    tag,
                    tag_type,
                    confidence,
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving semantic tag: {e}")
    
    def semantic_search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Perform semantic search across the knowledge graph"""
        try:
            results = []
            query_lower = query.lower()
            
            kg_db_path = Path.home() / ".automata02" / "knowledge_graph.sqlite"
            with sqlite3.connect(str(kg_db_path)) as conn:
                cursor = conn.cursor()
                
                # Search entities
                cursor.execute('''
                    SELECT e.entity_id, e.entity_type, e.name, e.metadata,
                           GROUP_CONCAT(em.file_path) as file_paths
                    FROM entities e
                    LEFT JOIN entity_mentions em ON e.entity_id = em.entity_id
                    WHERE LOWER(e.name) LIKE ? OR LOWER(e.metadata) LIKE ?
                    GROUP BY e.entity_id
                    LIMIT ?
                ''', (f'%{query_lower}%', f'%{query_lower}%', limit))
                
                for row in cursor.fetchall():
                    results.append({
                        'type': 'entity',
                        'entity_id': row[0],
                        'entity_type': row[1],
                        'name': row[2],
                        'metadata': json.loads(row[3] or '{}'),
                        'file_paths': row[4].split(',') if row[4] else [],
                        'score': self._calculate_semantic_score(query, row[2])
                    })
                
                # Search semantic tags
                cursor.execute('''
                    SELECT DISTINCT st.file_path, st.tag, st.tag_type, st.confidence
                    FROM semantic_tags st
                    WHERE LOWER(st.tag) LIKE ?
                    LIMIT ?
                ''', (f'%{query_lower}%', limit))
                
                for row in cursor.fetchall():
                    results.append({
                        'type': 'semantic_tag',
                        'file_path': row[0],
                        'tag': row[1],
                        'tag_type': row[2],
                        'confidence': row[3],
                        'score': self._calculate_semantic_score(query, row[1])
                    })
            
            # Sort by score
            results.sort(key=lambda x: x['score'], reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def _calculate_semantic_score(self, query: str, target: str) -> float:
        """Calculate semantic similarity score"""
        query_lower = query.lower()
        target_lower = target.lower()
        
        # Exact match
        if query_lower == target_lower:
            return 1.0
        
        # Contains match
        if query_lower in target_lower:
            return 0.8
        
        # Word overlap
        query_words = set(query_lower.split())
        target_words = set(target_lower.split())
        
        if query_words and target_words:
            overlap = len(query_words.intersection(target_words))
            union = len(query_words.union(target_words))
            return overlap / union
        
        return 0.0
    
    def get_related_files(self, file_path: str, relationship_types: List[str] = None) -> List[Dict[str, Any]]:
        """Get files related to the given file"""
        try:
            file_id = self._generate_entity_id(file_path)
            
            if file_id not in self.graph:
                return []
            
            related_files = []
            
            # Get connected entities
            connected_entities = list(self.graph.neighbors(file_id))
            
            # Find other files connected to the same entities
            for entity_id in connected_entities:
                entity_neighbors = list(self.graph.neighbors(entity_id))
                
                for neighbor_id in entity_neighbors:
                    if neighbor_id != file_id and self.graph.nodes[neighbor_id].get('entity_type') == 'file':
                        related_files.append({
                            'file_path': self.graph.nodes[neighbor_id]['metadata']['path'],
                            'relationship_via': self.graph.nodes[entity_id]['name'],
                            'entity_type': self.graph.nodes[entity_id]['entity_type'],
                            'strength': 1.0  # Could calculate based on edge weights
                        })
            
            # Remove duplicates and sort by strength
            seen = set()
            unique_files = []
            for file_info in related_files:
                if file_info['file_path'] not in seen:
                    seen.add(file_info['file_path'])
                    unique_files.append(file_info)
            
            unique_files.sort(key=lambda x: x['strength'], reverse=True)
            
            return unique_files
            
        except Exception as e:
            logger.error(f"Error getting related files: {e}")
            return []
    
    def get_entity_graph(self, entity_type: str = None) -> Dict[str, Any]:
        """Get graph representation of entities"""
        try:
            nodes = []
            edges = []
            
            for node_id, node_data in self.graph.nodes(data=True):
                if entity_type is None or node_data.get('entity_type') == entity_type:
                    nodes.append({
                        'id': node_id,
                        'label': node_data.get('name', node_id),
                        'type': node_data.get('entity_type', 'unknown'),
                        'metadata': node_data.get('metadata', {})
                    })
            
            for source, target, edge_data in self.graph.edges(data=True):
                if (entity_type is None or 
                    self.graph.nodes[source].get('entity_type') == entity_type or
                    self.graph.nodes[target].get('entity_type') == entity_type):
                    edges.append({
                        'source': source,
                        'target': target,
                        'type': edge_data.get('relationship_type', 'related'),
                        'weight': edge_data.get('weight', 1.0)
                    })
            
            return {
                'nodes': nodes,
                'edges': edges,
                'stats': {
                    'total_nodes': len(nodes),
                    'total_edges': len(edges)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting entity graph: {e}")
            return {'nodes': [], 'edges': [], 'stats': {'total_nodes': 0, 'total_edges': 0}}
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics"""
        try:
            kg_db_path = Path.home() / ".automata02" / "knowledge_graph.sqlite"
            with sqlite3.connect(str(kg_db_path)) as conn:
                cursor = conn.cursor()
                
                # Entity counts by type
                cursor.execute('''
                    SELECT entity_type, COUNT(*) 
                    FROM entities 
                    GROUP BY entity_type
                ''')
                entity_counts = dict(cursor.fetchall())
                
                # Total relationships
                cursor.execute('SELECT COUNT(*) FROM relationships')
                total_relationships = cursor.fetchone()[0]
                
                # Total mentions
                cursor.execute('SELECT COUNT(*) FROM entity_mentions')
                total_mentions = cursor.fetchone()[0]
                
                # Total semantic tags
                cursor.execute('SELECT COUNT(*) FROM semantic_tags')
                total_tags = cursor.fetchone()[0]
                
                return {
                    'total_entities': sum(entity_counts.values()),
                    'entity_counts': entity_counts,
                    'total_relationships': total_relationships,
                    'total_mentions': total_mentions,
                    'total_semantic_tags': total_tags,
                    'graph_density': self._calculate_graph_density()
                }
                
        except Exception as e:
            logger.error(f"Error getting graph stats: {e}")
            return {}
    
    def _calculate_graph_density(self) -> float:
        """Calculate graph density"""
        try:
            num_nodes = self.graph.number_of_nodes()
            num_edges = self.graph.number_of_edges()
            
            if num_nodes < 2:
                return 0.0
            
            max_edges = num_nodes * (num_nodes - 1)
            return num_edges / max_edges if max_edges > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating graph density: {e}")
            return 0.0
    
    def _load_graph(self):
        """Load existing graph from database"""
        try:
            kg_db_path = Path.home() / ".automata02" / "knowledge_graph.sqlite"
            if not Path(kg_db_path).exists():
                return
                
            with sqlite3.connect(str(kg_db_path)) as conn:
                cursor = conn.cursor()
                
                # Load entities
                cursor.execute('SELECT * FROM entities LIMIT 1000')  # Limit for performance
                for row in cursor.fetchall():
                    entity_id, entity_type, name, metadata_json, created_at, updated_at = row
                    metadata = json.loads(metadata_json or '{}')
                    
                    self.graph.add_node(entity_id, 
                                      entity_type=entity_type,
                                      name=name,
                                      metadata=metadata)
                
                # Load relationships
                cursor.execute('SELECT source_id, target_id, relationship_type, weight FROM relationships LIMIT 5000')
                for row in cursor.fetchall():
                    source_id, target_id, relationship_type, weight = row
                    
                    if source_id in self.graph and target_id in self.graph:
                        self.graph.add_edge(source_id, target_id,
                                          relationship_type=relationship_type,
                                          weight=weight)
                
                logger.info(f"Loaded knowledge graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
                
        except Exception as e:
            logger.error(f"Error loading graph: {e}")