"""
Neo4j graph database service.
Falls back to in-memory graph when Neo4j is unavailable.
"""
import os
import uuid
import logging
from typing import List, Dict, Optional, Any, Tuple

logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


class InMemoryGraph:
    """Fallback in-memory graph when Neo4j is not available."""

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[Dict] = []

    def add_node(self, node_id: str, label: str, node_type: str,
                 description: str = "", confidence: float = 1.0,
                 session_id: str = "", properties: Dict = None):
        self.nodes[node_id] = {
            "id": node_id, "label": label, "type": node_type,
            "description": description, "confidence": confidence,
            "session_id": session_id, "properties": properties or {}
        }

    def add_edge(self, from_id: str, to_id: str, rel_type: str,
                 weight: float = 1.0, condition: Optional[str] = None,
                 is_hard_edge: bool = False, session_id: str = "") -> str:
        edge_id = str(uuid.uuid4())
        self.edges.append({
            "id": edge_id, "from_node": from_id, "to_node": to_id,
            "type": rel_type, "weight": weight, "condition": condition,
            "is_hard_edge": is_hard_edge, "session_id": session_id
        })
        return edge_id

    def get_nodes(self, session_id: str) -> List[Dict]:
        return [n for n in self.nodes.values() if n.get("session_id") == session_id]

    def get_edges(self, session_id: str) -> List[Dict]:
        node_ids = {n["id"] for n in self.get_nodes(session_id)}
        return [e for e in self.edges
                if e["from_node"] in node_ids and e["to_node"] in node_ids]

    def get_node_degree(self, node_id: str, session_id: str) -> int:
        edges = self.get_edges(session_id)
        return sum(1 for e in edges if e["from_node"] == node_id or e["to_node"] == node_id)

    def delete_node(self, node_id: str):
        self.nodes.pop(node_id, None)
        self.edges = [e for e in self.edges
                      if e["from_node"] != node_id and e["to_node"] != node_id]

    def get_neighbors(self, node_id: str, session_id: str) -> List[Tuple[str, str, float]]:
        """Returns (neighbor_id, rel_type, weight) tuples."""
        result = []
        for e in self.get_edges(session_id):
            if e["from_node"] == node_id:
                result.append((e["to_node"], e["type"], e["weight"]))
            elif e["to_node"] == node_id:
                result.append((e["from_node"], e["type"], e["weight"]))
        return result

    def get_all_node_ids(self, session_id: str) -> List[str]:
        return [n["id"] for n in self.get_nodes(session_id)]

    def node_exists(self, node_id: str) -> bool:
        return node_id in self.nodes


class Neo4jService:
    def __init__(self):
        self.driver = None
        self.fallback = InMemoryGraph()
        self._try_connect()

    def _try_connect(self):
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(
                NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            self.driver.verify_connectivity()
            logger.info("Connected to Neo4j at %s", NEO4J_URI)
        except Exception as e:
            logger.warning("Neo4j unavailable (%s). Using in-memory graph.", e)
            self.driver = None

    @property
    def using_neo4j(self) -> bool:
        return self.driver is not None

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def create_node(self, node_id: str, label: str, node_type: str,
                    description: str = "", confidence: float = 1.0,
                    session_id: str = "", properties: Dict = None) -> bool:
        if not self.driver:
            self.fallback.add_node(node_id, label, node_type, description,
                                   confidence, session_id, properties or {})
            return True
        try:
            with self.driver.session() as s:
                s.run(
                    """MERGE (n:KGNode {id: $id, session_id: $sid})
                    SET n.label=$label, n.type=$type, n.description=$desc,
                        n.confidence=$conf""",
                    id=node_id, sid=session_id, label=label, type=node_type,
                    desc=description, conf=confidence
                )
            return True
        except Exception as e:
            logger.error("Neo4j create_node error: %s", e)
            self.fallback.add_node(node_id, label, node_type, description,
                                   confidence, session_id, properties or {})
            return True

    def create_edge(self, from_id: str, to_id: str, rel_type: str,
                    weight: float = 1.0, condition: Optional[str] = None,
                    is_hard_edge: bool = False, session_id: str = "") -> str:
        edge_id = str(uuid.uuid4())
        if not self.driver:
            return self.fallback.add_edge(from_id, to_id, rel_type, weight,
                                          condition, is_hard_edge, session_id)
        try:
            with self.driver.session() as s:
                s.run(
                    f"""MATCH (a:KGNode {{id: $from_id, session_id: $sid}})
                    MATCH (b:KGNode {{id: $to_id, session_id: $sid}})
                    MERGE (a)-[r:{rel_type} {{id: $eid, session_id: $sid}}]->(b)
                    SET r.weight=$weight, r.condition=$cond, r.is_hard=$hard""",
                    from_id=from_id, to_id=to_id, sid=session_id,
                    eid=edge_id, weight=weight, cond=condition, hard=is_hard_edge
                )
            return edge_id
        except Exception as e:
            logger.error("Neo4j create_edge error: %s", e)
            return self.fallback.add_edge(from_id, to_id, rel_type, weight,
                                          condition, is_hard_edge, session_id)

    def get_all_nodes(self, session_id: str) -> List[Dict]:
        if not self.driver:
            return self.fallback.get_nodes(session_id)
        try:
            with self.driver.session() as s:
                result = s.run(
                    "MATCH (n:KGNode {session_id: $sid}) RETURN n",
                    sid=session_id
                )
                return [dict(r["n"]) for r in result]
        except Exception as e:
            logger.error("Neo4j get_all_nodes error: %s", e)
            return self.fallback.get_nodes(session_id)

    def get_all_edges(self, session_id: str) -> List[Dict]:
        if not self.driver:
            return self.fallback.get_edges(session_id)
        try:
            with self.driver.session() as s:
                result = s.run(
                    """MATCH (a:KGNode {session_id: $sid})-[r]->(b:KGNode {session_id: $sid})
                    RETURN r, a.id as from_node, b.id as to_node, type(r) as rel_type""",
                    sid=session_id
                )
                edges = []
                for row in result:
                    props = dict(row["r"])
                    props["from_node"] = row["from_node"]
                    props["to_node"] = row["to_node"]
                    props["type"] = row["rel_type"]
                    edges.append(props)
                return edges
        except Exception as e:
            logger.error("Neo4j get_all_edges error: %s", e)
            return self.fallback.get_edges(session_id)

    def get_node_degree(self, node_id: str, session_id: str) -> int:
        if not self.driver:
            return self.fallback.get_node_degree(node_id, session_id)
        try:
            with self.driver.session() as s:
                r = s.run(
                    """MATCH (n:KGNode {id: $id, session_id: $sid})-[r]-()
                    RETURN count(r) as degree""",
                    id=node_id, sid=session_id
                )
                row = r.single()
                return row["degree"] if row else 0
        except Exception:
            return self.fallback.get_node_degree(node_id, session_id)

    def delete_node(self, node_id: str, session_id: str):
        if not self.driver:
            self.fallback.delete_node(node_id)
            return
        try:
            with self.driver.session() as s:
                s.run(
                    "MATCH (n:KGNode {id: $id, session_id: $sid}) DETACH DELETE n",
                    id=node_id, sid=session_id
                )
        except Exception as e:
            logger.error("Neo4j delete_node error: %s", e)
            self.fallback.delete_node(node_id)

    def get_neighbors(self, node_id: str, session_id: str) -> List[Tuple[str, str, float]]:
        if not self.driver:
            return self.fallback.get_neighbors(node_id, session_id)
        try:
            with self.driver.session() as s:
                result = s.run(
                    """MATCH (a:KGNode {id: $id, session_id: $sid})-[r]-(b:KGNode)
                    RETURN b.id as neighbor, type(r) as rel_type,
                           coalesce(r.weight, 1.0) as weight""",
                    id=node_id, sid=session_id
                )
                return [(row["neighbor"], row["rel_type"], row["weight"]) for row in result]
        except Exception:
            return self.fallback.get_neighbors(node_id, session_id)

    def node_exists(self, node_id: str, session_id: str) -> bool:
        if not self.driver:
            return self.fallback.node_exists(node_id)
        try:
            with self.driver.session() as s:
                r = s.run(
                    "MATCH (n:KGNode {id: $id, session_id: $sid}) RETURN count(n) as cnt",
                    id=node_id, sid=session_id
                )
                row = r.single()
                return bool(row and row["cnt"] > 0)
        except Exception:
            return self.fallback.node_exists(node_id)

    def get_all_node_ids(self, session_id: str) -> List[str]:
        if not self.driver:
            return self.fallback.get_all_node_ids(session_id)
        try:
            with self.driver.session() as s:
                result = s.run(
                    "MATCH (n:KGNode {session_id: $sid}) RETURN n.id as id",
                    sid=session_id
                )
                return [row["id"] for row in result]
        except Exception:
            return self.fallback.get_all_node_ids(session_id)

    def clear_session(self, session_id: str):
        if not self.driver:
            node_ids = self.fallback.get_all_node_ids(session_id)
            for nid in node_ids:
                self.fallback.delete_node(nid)
            return
        try:
            with self.driver.session() as s:
                s.run(
                    "MATCH (n:KGNode {session_id: $sid}) DETACH DELETE n",
                    sid=session_id
                )
        except Exception as e:
            logger.error("Neo4j clear_session error: %s", e)

    def close(self):
        if self.driver:
            self.driver.close()


# Singleton
_neo4j: Optional[Neo4jService] = None


def get_neo4j() -> Neo4jService:
    global _neo4j
    if _neo4j is None:
        _neo4j = Neo4jService()
    return _neo4j
