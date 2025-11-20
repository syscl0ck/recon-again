"""
Base classes for reconnaissance tools
All tools inherit from BaseTool and implement the run() method
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Standard result format for all tools"""
    tool_name: str
    target: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'tool_name': self.tool_name,
            'target': self.target,
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'execution_time': self.execution_time,
            'metadata': self.metadata,
            'timestamp': self.timestamp
        }


class BaseTool(ABC):
    """
    Base class for all reconnaissance tools
    Provides common functionality and enforces interface
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize tool with configuration
        
        Args:
            config: Global configuration dictionary
        """
        self.config = config
        self.timeout = config.get('tools', {}).get('timeout', 300)
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier name"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable tool description"""
        pass
    
    @property
    @abstractmethod
    def category(self) -> str:
        """Tool category (e.g., 'dns', 'web', 'api')"""
        pass
    
    @property
    def requires_auth(self) -> bool:
        """Whether tool requires authentication"""
        return False
    
    @abstractmethod
    async def run(self, target: str) -> ToolResult:
        """
        Execute the tool against a target
        
        Args:
            target: Target domain, IP, or identifier
            
        Returns:
            ToolResult with findings
        """
        pass
    
    def _create_result(
        self,
        target: str,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        execution_time: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Helper to create standardized ToolResult"""
        return ToolResult(
            tool_name=self.name,
            target=target,
            success=success,
            data=data,
            error=error,
            execution_time=execution_time,
            metadata=metadata or {}
        )

