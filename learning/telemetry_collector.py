"""Telemetry Collector - Collects and stores telemetry data and message logs."""

from typing import List, Dict, Any, Optional
from datetime import datetime
import sqlite3
from pathlib import Path
import json

from core.message import Telemetry


class TelemetryCollector:
    """Collects and stores telemetry from agents."""

    def __init__(self, db_path: str = "state/telemetry.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize telemetry database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                action TEXT NOT NULL,
                success INTEGER NOT NULL,
                cost REAL NOT NULL,
                duration_ms REAL NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Persist all bus communications/messages across runs
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage TEXT NOT NULL,              -- 'published' | 'dispatched'
                message_id TEXT,
                type TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                receiver_id TEXT,                -- may be NULL for broadcast publish
                content TEXT,
                timestamp TEXT NOT NULL,
                tags TEXT,                       -- JSON array
                metadata TEXT,                   -- JSON object
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.commit()
        conn.close()

    def collect(self, telemetry: Telemetry):
        """Collect and store telemetry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO telemetry (agent_id, action, success, cost, duration_ms, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                telemetry.agent_id,
                telemetry.action,
                1 if telemetry.success else 0,
                telemetry.cost,
                telemetry.duration_ms,
                telemetry.timestamp.isoformat(),
                str(telemetry.metadata),
            ),
        )

        conn.commit()
        conn.close()

    def record_message(
        self,
        *,
        stage: str,
        message_id: Optional[str],
        message_type: str,
        sender_id: str,
        receiver_id: Optional[str],
        content: str,
        timestamp: str,
        tags: Optional[list],
        metadata: Optional[dict],
    ) -> None:
        """Persist a bus message (published or dispatched) to the messages table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO messages (stage, message_id, type, sender_id, receiver_id, content, timestamp, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stage,
                message_id,
                message_type,
                sender_id,
                receiver_id,
                content,
                timestamp,
                json.dumps(tags or []),
                json.dumps(metadata or {}),
            ),
        )

        conn.commit()
        conn.close()

    def query(self, agent_id: str = None, since: datetime = None) -> List[Dict[str, Any]]:
        """Query telemetry data."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        conditions = []
        params = []

        if agent_id:
            conditions.append("agent_id = ?")
            params.append(agent_id)

        if since:
            conditions.append("timestamp >= ?")
            params.append(since.isoformat())

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cursor.execute(
            f"""
            SELECT * FROM telemetry {where_clause}
            ORDER BY timestamp DESC
        """,
            params,
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]
