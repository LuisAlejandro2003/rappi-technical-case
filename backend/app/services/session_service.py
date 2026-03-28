import json
import sqlite3
import uuid
from datetime import datetime

from app.models.schemas import Message, Session


class SessionService:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                summary TEXT,
                title TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sql_query TEXT,
                visualization TEXT,
                timestamp TEXT NOT NULL
            );
        """)
        self.conn.commit()

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        now = datetime.now(tz=None).isoformat()
        self.conn.execute(
            "INSERT INTO sessions (id, created_at) VALUES (?, ?)",
            (session_id, now),
        )
        self.conn.commit()
        return session_id

    def get_session(self, session_id: str) -> Session | None:
        row = self.conn.execute(
            "SELECT id, created_at, summary, title FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            return None
        messages = self._get_messages(session_id)
        return Session(
            id=row[0],
            created_at=datetime.fromisoformat(row[1]),
            messages=messages,
            summary=row[2],
            title=row[3],
        )

    def add_message(self, session_id: str, message: Message) -> None:
        viz_json = message.visualization.model_dump_json() if message.visualization else None
        self.conn.execute(
            "INSERT INTO messages (session_id, role, content, sql_query, visualization, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, message.role, message.content, message.sql_query, viz_json, message.timestamp.isoformat()),
        )
        self.conn.commit()

    def list_sessions(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT s.id, s.created_at, s.title, "
            "(SELECT m.content FROM messages m WHERE m.session_id = s.id ORDER BY m.id ASC LIMIT 1) as first_message "
            "FROM sessions s ORDER BY s.created_at DESC"
        ).fetchall()
        return [
            {"id": r[0], "created_at": r[1], "title": r[2], "first_message": r[3]}
            for r in rows
        ]

    def get_messages_window(self, session_id: str, max_turns: int = 5) -> list[Message]:
        """Return the last N turns (user+assistant pairs) for context window."""
        all_messages = self._get_messages(session_id)
        if not all_messages:
            return []
        # A turn is a user message + assistant response
        # Take last max_turns * 2 messages (approximate)
        window_size = max_turns * 2
        return all_messages[-window_size:]

    def _get_messages(self, session_id: str) -> list[Message]:
        rows = self.conn.execute(
            "SELECT role, content, sql_query, visualization, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        messages = []
        for r in rows:
            viz = None
            if r[3]:
                from app.models.schemas import VizConfig
                viz = VizConfig.model_validate_json(r[3])
            messages.append(Message(
                role=r[0], content=r[1], sql_query=r[2],
                visualization=viz, timestamp=datetime.fromisoformat(r[4]),
            ))
        return messages
