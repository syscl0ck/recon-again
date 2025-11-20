"""
Database models for recon-again
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from .connection import get_db

logger = logging.getLogger(__name__)


@dataclass
class Target:
    """Target model"""
    id: Optional[int] = None
    target: str = ""
    target_type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def save(self) -> int:
        """Save target to database"""
        db = get_db()
        
        # Check if target exists
        existing = db.fetchone(
            "SELECT id FROM targets WHERE target = ?",
            (self.target,)
        )
        
        if existing:
            self.id = existing['id']
            # Update
            db.execute(
                """UPDATE targets 
                   SET updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (self.id,)
            )
            return self.id
        else:
            # Insert
            cursor = db.execute(
                """INSERT INTO targets (target, target_type) 
                   VALUES (?, ?)""",
                (self.target, self.target_type)
            )
            self.id = cursor.lastrowid
            return self.id
    
    @classmethod
    def get_or_create(cls, target: str, target_type: Optional[str] = None) -> 'Target':
        """Get existing target or create new one"""
        db = get_db()
        row = db.fetchone("SELECT * FROM targets WHERE target = ?", (target,))
        
        if row:
            return cls.from_row(row)
        else:
            target_obj = cls(target=target, target_type=target_type)
            target_obj.save()
            return target_obj
    
    @classmethod
    def from_row(cls, row) -> 'Target':
        """Create Target from database row"""
        return cls(
            id=row['id'],
            target=row['target'],
            target_type=row['target_type'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )


@dataclass
class Session:
    """Session model"""
    id: Optional[int] = None
    session_id: str = ""
    target_id: int = 0
    status: str = "running"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tools_executed: List[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.tools_executed is None:
            self.tools_executed = []
    
    def save(self) -> int:
        """Save session to database"""
        db = get_db()
        
        tools_json = json.dumps(self.tools_executed)
        start_time_str = self.start_time.isoformat() if self.start_time else None
        end_time_str = self.end_time.isoformat() if self.end_time else None
        
        if self.id:
            # Update
            db.execute(
                """UPDATE sessions 
                   SET status = ?, end_time = ?, tools_executed = ?
                   WHERE id = ?""",
                (self.status, end_time_str, tools_json, self.id)
            )
            return self.id
        else:
            # Insert
            cursor = db.execute(
                """INSERT INTO sessions (session_id, target_id, status, start_time, tools_executed)
                   VALUES (?, ?, ?, ?, ?)""",
                (self.session_id, self.target_id, self.status, start_time_str, tools_json)
            )
            self.id = cursor.lastrowid
            return self.id
    
    def complete(self):
        """Mark session as completed"""
        self.status = "completed"
        self.end_time = datetime.now()
        self.save()
    
    @classmethod
    def from_row(cls, row) -> 'Session':
        """Create Session from database row"""
        tools_executed = json.loads(row['tools_executed']) if row['tools_executed'] else []
        return cls(
            id=row['id'],
            session_id=row['session_id'],
            target_id=row['target_id'],
            status=row['status'],
            start_time=datetime.fromisoformat(row['start_time']) if row['start_time'] else None,
            end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
            tools_executed=tools_executed,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )
    
    @classmethod
    def get_by_session_id(cls, session_id: str) -> Optional['Session']:
        """Get session by session_id"""
        db = get_db()
        row = db.fetchone("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        return cls.from_row(row) if row else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'target_id': self.target_id,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'tools_executed': self.tools_executed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class ToolResult:
    """Tool result model"""
    id: Optional[int] = None
    session_id: str = ""
    tool_name: str = ""
    target: str = ""
    success: bool = False
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def save(self) -> int:
        """Save tool result to database"""
        db = get_db()
        
        data_json = json.dumps(self.data) if self.data is not None else None
        metadata_json = json.dumps(self.metadata) if self.metadata else None
        timestamp_str = self.timestamp.isoformat() if self.timestamp else None
        
        cursor = db.execute(
            """INSERT INTO tool_results 
               (session_id, tool_name, target, success, data, error, execution_time, metadata, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.session_id, self.tool_name, self.target, 1 if self.success else 0,
             data_json, self.error, self.execution_time, metadata_json, timestamp_str)
        )
        self.id = cursor.lastrowid
        return self.id
    
    @classmethod
    def from_row(cls, row) -> 'ToolResult':
        """Create ToolResult from database row"""
        data = json.loads(row['data']) if row['data'] else None
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        return cls(
            id=row['id'],
            session_id=row['session_id'],
            tool_name=row['tool_name'],
            target=row['target'],
            success=bool(row['success']),
            data=data,
            error=row['error'],
            execution_time=row['execution_time'],
            metadata=metadata,
            timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None
        )
    
    @classmethod
    def get_by_session(cls, session_id: str) -> List['ToolResult']:
        """Get all tool results for a session"""
        db = get_db()
        rows = db.fetchall(
            "SELECT * FROM tool_results WHERE session_id = ? ORDER BY timestamp",
            (session_id,)
        )
        return [cls.from_row(row) for row in rows]


@dataclass
class AIAnalysis:
    """AI analysis model"""
    id: Optional[int] = None
    session_id: str = ""
    target: str = ""
    summary: Optional[str] = None
    key_findings: List[str] = None
    recommendations: List[str] = None
    risk_level: Optional[str] = None
    interesting_targets: List[str] = None
    analysis_data: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.key_findings is None:
            self.key_findings = []
        if self.recommendations is None:
            self.recommendations = []
        if self.interesting_targets is None:
            self.interesting_targets = []
        if self.analysis_data is None:
            self.analysis_data = {}
    
    def save(self) -> int:
        """Save AI analysis to database"""
        db = get_db()
        
        key_findings_json = json.dumps(self.key_findings)
        recommendations_json = json.dumps(self.recommendations)
        interesting_targets_json = json.dumps(self.interesting_targets)
        analysis_data_json = json.dumps(self.analysis_data)
        
        if self.id:
            # Update
            db.execute(
                """UPDATE ai_analysis 
                   SET summary = ?, key_findings = ?, recommendations = ?, 
                       risk_level = ?, interesting_targets = ?, analysis_data = ?
                   WHERE id = ?""",
                (self.summary, key_findings_json, recommendations_json,
                 self.risk_level, interesting_targets_json, analysis_data_json, self.id)
            )
            return self.id
        else:
            # Insert
            cursor = db.execute(
                """INSERT INTO ai_analysis 
                   (session_id, target, summary, key_findings, recommendations, 
                    risk_level, interesting_targets, analysis_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (self.session_id, self.target, self.summary, key_findings_json,
                 recommendations_json, self.risk_level, interesting_targets_json, analysis_data_json)
            )
            self.id = cursor.lastrowid
            return self.id
    
    @classmethod
    def from_row(cls, row) -> 'AIAnalysis':
        """Create AIAnalysis from database row"""
        key_findings = json.loads(row['key_findings']) if row['key_findings'] else []
        recommendations = json.loads(row['recommendations']) if row['recommendations'] else []
        interesting_targets = json.loads(row['interesting_targets']) if row['interesting_targets'] else []
        analysis_data = json.loads(row['analysis_data']) if row['analysis_data'] else {}
        
        return cls(
            id=row['id'],
            session_id=row['session_id'],
            target=row['target'],
            summary=row['summary'],
            key_findings=key_findings,
            recommendations=recommendations,
            risk_level=row['risk_level'],
            interesting_targets=interesting_targets,
            analysis_data=analysis_data,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )
    
    @classmethod
    def get_by_session(cls, session_id: str) -> Optional['AIAnalysis']:
        """Get AI analysis for a session"""
        db = get_db()
        row = db.fetchone("SELECT * FROM ai_analysis WHERE session_id = ?", (session_id,))
        return cls.from_row(row) if row else None


class Database:
    """Database operations wrapper"""
    
    @staticmethod
    def get_session(session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return Session.get_by_session_id(session_id)
    
    @staticmethod
    def get_tool_results(session_id: str) -> List[ToolResult]:
        """Get all tool results for a session"""
        return ToolResult.get_by_session(session_id)
    
    @staticmethod
    def get_ai_analysis(session_id: str) -> Optional[AIAnalysis]:
        """Get AI analysis for a session"""
        return AIAnalysis.get_by_session(session_id)
    
    @staticmethod
    def list_sessions(limit: int = 50, status: Optional[str] = None) -> List[Session]:
        """List recent sessions"""
        db = get_db()
        if status:
            rows = db.fetchall(
                """SELECT s.* FROM sessions s 
                   WHERE s.status = ? 
                   ORDER BY s.start_time DESC LIMIT ?""",
                (status, limit)
            )
        else:
            rows = db.fetchall(
                """SELECT s.* FROM sessions s 
                   ORDER BY s.start_time DESC LIMIT ?""",
                (limit,)
            )
        return [Session.from_row(row) for row in rows]
    
    @staticmethod
    def get_target_stats(target: str) -> Dict[str, Any]:
        """Get statistics for a target"""
        db = get_db()
        
        # Get target
        target_row = db.fetchone("SELECT * FROM targets WHERE target = ?", (target,))
        if not target_row:
            return {}
        
        # Get session count
        session_count = db.fetchone(
            "SELECT COUNT(*) as count FROM sessions WHERE target_id = ?",
            (target_row['id'],)
        )['count']
        
        # Get tool results count
        tool_results_count = db.fetchone(
            """SELECT COUNT(*) as count FROM tool_results tr
               JOIN sessions s ON tr.session_id = s.session_id
               WHERE s.target_id = ?""",
            (target_row['id'],)
        )['count']
        
        # Get latest session
        latest_session = db.fetchone(
            """SELECT * FROM sessions 
               WHERE target_id = ? 
               ORDER BY start_time DESC LIMIT 1""",
            (target_row['id'],)
        )
        
        return {
            'target': target,
            'target_id': target_row['id'],
            'session_count': session_count,
            'tool_results_count': tool_results_count,
            'latest_session': Session.from_row(latest_session).to_dict() if latest_session else None
        }

