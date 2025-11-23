"""Neo4j graph database integration."""

import logging
import os
from typing import Iterable, List, Optional

try:
    from neo4j import GraphDatabase  # type: ignore
except ImportError:  # pragma: no cover - handled at runtime
    GraphDatabase = None

logger = logging.getLogger(__name__)


class GraphDatabaseClient:
    """Lightweight Neo4j client for contact graph storage."""

    def __init__(
        self,
        uri: Optional[str],
        user: Optional[str],
        password: Optional[str],
        database: Optional[str] = None,
        enabled: bool = True,
    ) -> None:
        self._driver = None
        self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")
        self.enabled = bool(enabled)

        if not enabled:
            logger.info("Neo4j graph database disabled by configuration")
            return

        if GraphDatabase is None:
            logger.warning("neo4j driver not installed; graph features disabled")
            self.enabled = False
            return

        if not uri or not user or not password:
            logger.info("Neo4j configuration incomplete; graph features disabled")
            self.enabled = False
            return

        try:
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info("Connected to Neo4j graph database at %s", uri)
        except Exception as exc:  # pragma: no cover - connection errors are runtime issues
            logger.error("Failed to connect to Neo4j: %s", exc)
            self.enabled = False

    @classmethod
    def from_config(cls, config: Optional[dict]) -> Optional["GraphDatabaseClient"]:
        graph_config = config or {}
        return cls(
            uri=graph_config.get("uri") or os.getenv("NEO4J_URI"),
            user=graph_config.get("user") or os.getenv("NEO4J_USER"),
            password=graph_config.get("password") or os.getenv("NEO4J_PASSWORD"),
            database=graph_config.get("database") or os.getenv("NEO4J_DATABASE"),
            enabled=graph_config.get("enabled", True),
        )

    def close(self) -> None:
        if self._driver:
            self._driver.close()
            self._driver = None

    def ingest_contacts(
        self,
        target: str,
        emails: Optional[Iterable[str]] = None,
        phones: Optional[Iterable[str]] = None,
        source: Optional[str] = None,
    ) -> None:
        if not self.enabled or not self._driver:
            return

        email_list = self._safe_list(emails)
        phone_list = self._safe_list(phones)
        if not email_list and not phone_list:
            return

        normalized_target = self._normalize_target(target)
        with self._driver.session(database=self.database) as session:
            for email in email_list:
                session.execute_write(
                    self._upsert_contact,
                    normalized_target,
                    email.lower(),
                    "email",
                    source,
                )
            for phone in phone_list:
                session.execute_write(
                    self._upsert_contact,
                    normalized_target,
                    self._normalize_phone(phone),
                    "phone",
                    source,
                )

    @staticmethod
    def _safe_list(values: Optional[Iterable[str]]) -> List[str]:
        if not values:
            return []
        return [value for value in values if value]

    @staticmethod
    def _normalize_target(target: str) -> str:
        sanitized = target.replace("https://", "").replace("http://", "").strip()
        return sanitized.rstrip("/")

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        digits = "".join(char for char in phone if char.isdigit() or char == "+")
        return digits or phone

    @staticmethod
    def _upsert_contact(tx, target: str, value: str, contact_type: str, source: Optional[str]):
        tx.run(
            """
            MERGE (t:Target {name: $target})
              ON CREATE SET t.createdAt = datetime()
              SET t.lastSeen = datetime()
            MERGE (c:Contact {value: $value, type: $type})
              ON CREATE SET c.createdAt = datetime()
              SET c.lastSeen = datetime(), c.source = $source
            MERGE (t)-[r:HAS_CONTACT {type: $type}]->(c)
              SET r.source = $source, r.lastSeen = datetime()
            """,
            target=target,
            value=value,
            type=contact_type,
            source=source,
        )


__all__ = ["GraphDatabaseClient"]
