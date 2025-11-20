"""Reconnaissance tools module"""

from .base import BaseTool, ToolResult

# API-based tools (free, no installation needed)
try:
    from .api_tools import CrtShTool, UrlscanTool, HIBPTool
except ImportError:
    CrtShTool = None
    UrlscanTool = None
    HIBPTool = None

# Python-based tools (require dependencies)
try:
    from .python_tools import Sublist3rTool, DNSReconTool, DirsearchTool, WaybackTool, SherlockTool
except ImportError:
    Sublist3rTool = None
    DNSReconTool = None
    DirsearchTool = None
    WaybackTool = None
    SherlockTool = None

__all__ = [
    'BaseTool',
    'ToolResult',
    'CrtShTool',
    'UrlscanTool',
    'HIBPTool',
    'Sublist3rTool',
    'DNSReconTool',
    'DirsearchTool',
    'WaybackTool',
    'SherlockTool'
]

