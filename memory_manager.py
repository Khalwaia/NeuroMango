import os
import logging
from typing import List, Dict
import chromadb
from chromadb.utils import embedding_functions
import config

logger = logging.getLogger("neuromango.memory")

class MemoryManager:
    def __init__(self):
        # Core Memory
        self.core_memory = ""
        self.load_core_memory()
                
    def load_core_memory(self):
        if config.CORE_MEMORY_PATH.exists():
            with open(config.CORE_MEMORY_PATH, "r", encoding="utf-8") as f:
                self.core_memory = f.read().strip()
                
        # Short Term Memory
        self.history: List[Dict[str, str]] = []
        self.max_history_length = 30  # Keep last 30 messages
        
        # Vector Database (ChromaDB)
        os.makedirs(config.CHROMA_DB_DIR, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=str(config.CHROMA_DB_DIR))
        
        # Embedding function
        # We use a fast, lightweight multilingual model or just standard sentence-transformers
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2" # good for russian and english
        )
        
        self.collection = self.chroma_client.get_or_create_collection(
            name="avatar_memory",
            embedding_function=self.embedding_fn
        )
        
        self.node_collection = self.chroma_client.get_or_create_collection(
            name="avatar_graph_nodes",
            embedding_function=self.embedding_fn
        )
        
        # Knowledge Graph (NetworkX)
        import networkx as nx
        import json
        self.graph_path = os.path.join(config.CHROMA_DB_DIR, "graph.json")
        self.graph = nx.DiGraph()
        self._load_graph()
        
        # Anti-loop Cache
        self.recent_memories_used = []
        
        # Memory Decay Parameters
        self.interaction_count = 0
        
    def _load_graph(self):
        import networkx as nx
        import json
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.graph = nx.node_link_graph(data)
            except Exception as e:
                logger.error(f"Failed to load graph: {e}")
                
    def _save_graph(self):
        import networkx as nx
        import json
        try:
            data = nx.node_link_data(self.graph)
            with open(self.graph_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save graph: {e}")
            
    def resolve_entity(self, entity_text: str) -> str:
        """Finds if a semantically similar entity already exists in the graph."""
        if not entity_text:
            return ""
            
        entity_lower = entity_text.strip().lower()
        if self.node_collection.count() == 0:
            return entity_lower
            
        results = self.node_collection.query(
            query_texts=[entity_lower],
            n_results=1
        )
        
        # Typically cosine distance < 0.2 means very similar.
        if results and results['distances'] and len(results['distances'][0]) > 0:
            distance = results['distances'][0][0]
            if distance < 0.2:  # Threshold for "same entity"
                matched_id = results['ids'][0][0]
                logger.info(f"🔗 Склеивание сущностей: '{entity_lower}' -> '{matched_id}' (dist: {distance:.3f})")
                return matched_id
                
        return entity_lower

    def decay_memory(self):
        """Reduces the weight of old connections. Removes forgotten ones."""
        edges_to_remove = []
        for u, v, data in self.graph.edges(data=True):
            last_accessed = data.get('last_accessed', 0)
            age = self.interaction_count - last_accessed
            
            # Simple linear decay: -0.01 weight per interaction not accessed (takes 100 interactions to forget)
            decay_amount = age * 0.01
            new_weight = max(0.0, data.get('weight', 1.0) - decay_amount)
            
            if new_weight < 0.1:
                edges_to_remove.append((u, v))
            else:
                self.graph[u][v]['weight'] = new_weight
                
        # Remove forgotten edges
        for u, v in edges_to_remove:
            self.graph.remove_edge(u, v)
            logger.info(f"🍂 Забывание: связь '{u}' -> '{v}' стерта из памяти.")
            
        # Remove orphaned nodes
        nodes_to_remove = [node for node in self.graph.nodes if self.graph.degree(node) == 0]
        for node in nodes_to_remove:
            self.graph.remove_node(node)
            logger.info(f"🍂 Забывание: узел '{node}' стерт из памяти.")

    def process_extracted_memory(self, extracted_data: dict):
        """Processes the JSON from the MemoryExtractor and updates DB and Graph."""
        if not extracted_data:
            return
            
        summary = extracted_data.get("summary", "")
        if summary and isinstance(summary, str) and len(summary) > 5:
            self.save_memory(summary)
            
        relations = extracted_data.get("relations", [])
        if relations and isinstance(relations, list):
            added = False
            for rel in relations:
                if isinstance(rel, list) and len(rel) == 3:
                    subj, pred, obj = rel
                    subj = str(subj).strip().lower()
                    obj = str(obj).strip().lower()
                    pred = str(pred).strip().lower()
                    if subj and obj and pred:
                        resolved_subj = self.resolve_entity(subj)
                        resolved_obj = self.resolve_entity(obj)
                        
                        if resolved_subj not in self.graph:
                            self.node_collection.add(documents=[subj], ids=[resolved_subj])
                        if resolved_obj not in self.graph:
                            self.node_collection.add(documents=[obj], ids=[resolved_obj])
                            
                        self.graph.add_edge(
                            resolved_subj, resolved_obj, 
                            relation=pred, 
                            weight=1.0, 
                            last_accessed=self.interaction_count
                        )
                        added = True
            if added:
                self.decay_memory() # Run decay before saving
                self._save_graph()
                logger.info(f"🕸️ [СВИНОПАС] Граф обновлен. Всего узлов: {self.graph.number_of_nodes()}")

    def get_relevant_graph_context(self, query: str, n_nodes: int = 2) -> str:
        """Retrieves subgraphs related to the query for prompt injection."""
        if self.node_collection.count() == 0 or self.graph.number_of_nodes() == 0:
            return ""
            
        results = self.node_collection.query(
            query_texts=[query],
            n_results=min(n_nodes, self.node_collection.count())
        )
        
        relevant_edges = []
        if results and results['ids'] and len(results['ids'][0]) > 0:
            for node_id in results['ids'][0]:
                if node_id in self.graph:
                    for v in self.graph.successors(node_id):
                        edge = self.graph[node_id][v]
                        rel = edge.get('relation', 'is')
                        # Boost memory since it was recalled
                        edge['weight'] = 1.0
                        edge['last_accessed'] = self.interaction_count
                        relevant_edges.append(f"{node_id} -> {rel} -> {v}")
                        
                    for u in self.graph.predecessors(node_id):
                        edge = self.graph[u][node_id]
                        rel = edge.get('relation', 'is')
                        # Boost memory since it was recalled
                        edge['weight'] = 1.0
                        edge['last_accessed'] = self.interaction_count
                        relevant_edges.append(f"{u} -> {rel} -> {node_id}")
                        
        if relevant_edges:
            relevant_edges = list(set(relevant_edges)) # deduplicate
            return "Knowledge Graph relations:\n" + "\n".join(relevant_edges)
        return ""
        
    def add_to_history(self, role: str, content: str):
        if role == "user":
            self.interaction_count += 1
            
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_history_length:
            self.history.pop(0)
            
    def get_history(self) -> List[Dict[str, str]]:
        return self.history
        
    def get_formatted_history(self) -> str:
        """Returns history formatted as a string for the prompt builder."""
        lines = []
        for msg in self.history:
            role_name = "User" if msg["role"] == "user" else "Avatar"
            lines.append(f"{role_name}: {msg['content']}")
        return "\n".join(lines)
        
    def save_memory(self, memory_text: str):
        """Saves a permanent memory to the vector database."""
        logger.info(f"💾 Saving to Vector DB: {memory_text}")
        doc_id = f"mem_{len(self.collection.get()['ids'])}"
        self.collection.add(
            documents=[memory_text],
            ids=[doc_id]
        )
        
    def get_similar_context(self, query: str, n_results: int = 3) -> str:
        """Retrieves semantically similar memories from the vector database."""
        if self.collection.count() == 0:
            return "Нет сохраненных воспоминаний в Timeline."
            
        results = self.collection.query(
            query_texts=[query],
            n_results=min(n_results, self.collection.count())
        )
        
        if results and 'documents' in results and results['documents'][0]:
            memories = results['documents'][0]
            return "\n".join([f"- {mem}" for mem in memories])
        return "Нет релевантных воспоминаний."
