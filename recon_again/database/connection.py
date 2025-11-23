"""
Database connection and initialization
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages SQLite database connection"""
    
    def __init__(self, db_path: str = "./data/recon_again.db"):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[sqlite3.Connection] = None
    
    def connect(self) -> sqlite3.Connection:
        """Get or create database connection"""
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Use row factory for dict-like access
            self._connection.row_factory = sqlite3.Row
            logger.info(f"Connected to database: {self.db_path}")
        return self._connection
    
    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions"""
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed, rolling back: {e}")
            raise
    
    def execute(self, query: str, params: tuple = ()):
        """Execute a query"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor
    
    def fetchall(self, query: str, params: tuple = ()):
        """Fetch all results"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def fetchone(self, query: str, params: tuple = ()):
        """Fetch one result"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()


# Global database instance
_db_instance: Optional[DatabaseConnection] = None


def get_db(db_path: Optional[str] = None) -> DatabaseConnection:
    """
    Get global database instance
    
    Args:
        db_path: Optional database path (only used on first call)
        
    Returns:
        DatabaseConnection instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseConnection(db_path or "./data/recon_again.db")
    return _db_instance


def init_db(db_path: Optional[str] = None):
    """
    Initialize database schema
    
    Args:
        db_path: Optional database path
    """
    db = get_db(db_path)
    
    schema = """
    -- Targets table
    CREATE TABLE IF NOT EXISTS targets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target TEXT NOT NULL UNIQUE,
        target_type TEXT,  -- 'domain', 'ip', 'email', etc.
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Sessions table
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL UNIQUE,
        target_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'running',
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP,
        tools_executed TEXT,  -- JSON array of tool names
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (target_id) REFERENCES targets(id) ON DELETE CASCADE
    );
    
    -- Tool results table
    CREATE TABLE IF NOT EXISTS tool_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        target TEXT NOT NULL,
        success INTEGER NOT NULL DEFAULT 0,  -- SQLite doesn't have boolean
        data TEXT,  -- JSON data
        error TEXT,
        execution_time REAL DEFAULT 0.0,
        metadata TEXT,  -- JSON metadata
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
    );
    
    -- AI analysis table
    CREATE TABLE IF NOT EXISTS ai_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL UNIQUE,
        target TEXT NOT NULL,
        summary TEXT,
        key_findings TEXT,  -- JSON array
        recommendations TEXT,  -- JSON array
        risk_level TEXT,
        interesting_targets TEXT,  -- JSON array
        analysis_data TEXT,  -- Full JSON analysis
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
    );

    -- Business intelligence table
    CREATE TABLE IF NOT EXISTS business_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL UNIQUE,
        target TEXT NOT NULL,
        business_size TEXT,
        incorporation_date TEXT,
        locations TEXT,  -- JSON array of locations/headquarters
        industry TEXT,
        other_insights TEXT,  -- JSON object for extra interesting facts
        source_tools TEXT,  -- JSON array of tool names used for analysis
        analysis_data TEXT,  -- Full JSON returned by AI
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
    );

    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_sessions_target ON sessions(target_id);
    CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
    CREATE INDEX IF NOT EXISTS idx_tool_results_session ON tool_results(session_id);
    CREATE INDEX IF NOT EXISTS idx_tool_results_tool ON tool_results(tool_name);
    CREATE INDEX IF NOT EXISTS idx_targets_target ON targets(target);
    CREATE INDEX IF NOT EXISTS idx_business_profiles_session ON business_profiles(session_id);
    """
    
    with db.transaction() as conn:
        conn.executescript(schema)
    
    logger.info("Database schema initialized")

