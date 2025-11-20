"""
recon-again: AI-powered reconnaissance framework
A modular, extensible recon tool with OpenRouter integration
"""

__version__ = "0.1.0"
__author__ = "recon-again team"

from .core.engine import ReconEngine
from .core.ai_pilot import AIPilot

__all__ = ['ReconEngine', 'AIPilot']

