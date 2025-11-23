"""Reconnaissance tools module"""

from .base import BaseTool, ToolResult

# API-based tools (free, no installation needed)
try:
    from .api_tools import (
        CrtShTool,
        UrlscanTool,
        HIBPTool,
        PhonebookTool,
        HunterTool,
        ClearbitProspectorTool,
        PeopleDataLabsTool
    )
except ImportError:
    CrtShTool = None
    UrlscanTool = None
    HIBPTool = None
    PhonebookTool = None
    HunterTool = None
    ClearbitProspectorTool = None
    PeopleDataLabsTool = None

# Python-based tools (require dependencies)
try:
    from .python_tools import (
        Sublist3rTool, DNSReconTool, WaybackTool, SherlockTool,
        TheHarvesterTool, GauTool, HoleheTool, MaigretTool, ArjunTool,
        EmailHarvesterTool
    )
except ImportError:
    Sublist3rTool = None
    DNSReconTool = None
    WaybackTool = None
    SherlockTool = None
    TheHarvesterTool = None
    GauTool = None
    HoleheTool = None
    MaigretTool = None
    ArjunTool = None
    EmailHarvesterTool = None

__all__ = [
    'BaseTool',
    'ToolResult',
    'CrtShTool',
    'UrlscanTool',
    'HIBPTool',
    'PhonebookTool',
    'HunterTool',
    'ClearbitProspectorTool',
    'PeopleDataLabsTool',
    'Sublist3rTool',
    'DNSReconTool',
    'WaybackTool',
    'SherlockTool',
    'TheHarvesterTool',
    'GauTool',
    'HoleheTool',
    'MaigretTool',
    'ArjunTool',
    'EmailHarvesterTool'
]

