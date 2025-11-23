"""
ReconEngine: The heart of recon-again
Orchestrates tool execution, result aggregation, and AI-driven automation
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from .ai_pilot import AIPilot
from ..tools.base import BaseTool, ToolResult as ToolResultBase
from ..database import (
    GraphDatabaseClient,
    AIAnalysis,
    BusinessProfile,
    Session,
    Target,
    ToolResult as DBToolResult,
    get_db,
    init_db,
)

logger = logging.getLogger(__name__)


@dataclass
class ReconSession:
    """Represents a reconnaissance session"""
    target: str
    session_id: str
    start_time: datetime
    tools_executed: List[str]
    results: Dict[str, Any]
    status: str = "running"
    
    def to_dict(self):
        return {
            **asdict(self),
            'start_time': self.start_time.isoformat()
        }


class ReconEngine:
    """
    Main engine for coordinating reconnaissance activities
    """
    
    def __init__(self, config_path: Optional[str] = None, enable_ai: bool = True, db_path: Optional[str] = None):
        """
        Initialize the recon engine
        
        Args:
            config_path: Path to configuration file
            enable_ai: Enable AI pilot for intelligent automation
            db_path: Path to SQLite database (default: ./data/recon_again.db)
        """
        self.config = self._load_config(config_path)
        self.ai_pilot = AIPilot(self.config.get('openrouter', {})) if enable_ai else None
        self.tools: Dict[str, BaseTool] = {}
        self.sessions: Dict[str, ReconSession] = {}
        self.results_dir = Path(self.config.get('results_dir', './results'))
        self.results_dir.mkdir(exist_ok=True)

        # Initialize graph database for contact intelligence
        self.graph_db = GraphDatabaseClient.from_config(self.config.get('graph', {}))
        if self.graph_db and not self.graph_db.enabled:
            self.graph_db = None

        # Initialize database
        db_path = db_path or self.config.get('db_path', './data/recon_again.db')
        init_db(db_path)
        self.db_path = db_path
        
        # Register available tools
        self._register_tools()
        
        logger.info(f"ReconEngine initialized with {len(self.tools)} tools")
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'results_dir': './results',
            'openrouter': {
                'api_key': None,
                'model': 'openai/gpt-4-turbo',
                'base_url': 'https://openrouter.ai/api/v1'
            },
            'hunter': {
                'api_key': None
            },
            'clearbit': {
                'api_key': None
            },
            'peopledatalabs': {
                'api_key': None
            },
            'tools': {
                'timeout': 300,
                'max_concurrent': 5
            },
            'graph': {
                'enabled': True,
                'uri': os.getenv('NEO4J_URI', 'bolt://neo4j:7687'),
                'user': os.getenv('NEO4J_USER', 'neo4j'),
                'password': os.getenv('NEO4J_PASSWORD', 'reconagain'),
                'database': os.getenv('NEO4J_DATABASE', 'neo4j')
            }
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def _register_tools(self):
        """Dynamically register all available tools"""
        from ..tools import (
            CrtShTool, UrlscanTool, HIBPTool, PhonebookTool,
            HunterTool, ClearbitProspectorTool, PeopleDataLabsTool,
            CloudEnumTool,
            Sublist3rTool, DNSReconTool,
            WaybackTool, SherlockTool,
            TheHarvesterTool, GauTool, HoleheTool, MaigretTool, ArjunTool,
            EmailHarvesterTool, CorporateSiteScraperTool, EmployeeSocialTool
        )

        tool_classes = [
            CrtShTool, UrlscanTool, HIBPTool, PhonebookTool,
            HunterTool, ClearbitProspectorTool, PeopleDataLabsTool,
            CloudEnumTool,
            Sublist3rTool, DNSReconTool,
            WaybackTool, SherlockTool,
            TheHarvesterTool, GauTool, HoleheTool, MaigretTool, ArjunTool,
            EmailHarvesterTool, CorporateSiteScraperTool, EmployeeSocialTool
        ]
        
        for tool_class in tool_classes:
            if tool_class is None:
                continue
            try:
                tool = tool_class(self.config)
                self.tools[tool.name] = tool
                logger.info(f"Registered tool: {tool.name}")
            except Exception as e:
                logger.warning(f"Failed to register {tool_class.__name__}: {e}")
    
    async def run_recon(
        self,
        target: str,
        tools: Optional[List[str]] = None,
        ai_guided: bool = True
    ) -> ReconSession:
        """
        Execute reconnaissance on a target
        
        Args:
            target: Target domain, IP, or identifier
            tools: Specific tools to run (None = all available)
            ai_guided: Use AI to determine best tool sequence
            
        Returns:
            ReconSession with results
        """
        session_id = f"{target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        # Create or get target in database
        target_obj = Target.get_or_create(target, target_type=self._detect_target_type(target))
        target_id = target_obj.id
        
        # Create session in database
        db_session = Session(
            session_id=session_id,
            target_id=target_id,
            status="running",
            start_time=start_time,
            tools_executed=[]
        )
        db_session.save()
        
        session = ReconSession(
            target=target,
            session_id=session_id,
            start_time=start_time,
            tools_executed=[],
            results={}
        )
        
        self.sessions[session_id] = session
        
        # Determine tool execution plan
        if ai_guided and self.ai_pilot:
            execution_plan = await self.ai_pilot.create_execution_plan(target, list(self.tools.keys()))
        else:
            execution_plan = tools or list(self.tools.keys())
        
        logger.info(f"Starting recon session {session_id} for {target}")
        logger.info(f"Execution plan: {execution_plan}")
        
        # Execute tools concurrently (with limits)
        semaphore = asyncio.Semaphore(self.config['tools']['max_concurrent'])
        
        async def run_tool(tool_name: str):
            if tool_name not in self.tools:
                logger.warning(f"Tool {tool_name} not found")
                return None
            
            async with semaphore:
                try:
                    tool = self.tools[tool_name]
                    logger.info(f"Executing {tool_name} on {target}")
                    result = await tool.run(target)
                    session.tools_executed.append(tool_name)
                    session.results[tool_name] = result.to_dict()
                    
                    # Save tool result to database
                    # Convert timestamp string to datetime if needed
                    timestamp = result.timestamp
                    if isinstance(timestamp, str):
                        try:
                            from datetime import datetime
                            timestamp = datetime.fromisoformat(timestamp)
                        except (ValueError, AttributeError):
                            timestamp = datetime.now()
                    elif timestamp is None:
                        from datetime import datetime
                        timestamp = datetime.now()
                    
                    db_result = DBToolResult(
                        session_id=session_id,
                        tool_name=tool_name,
                        target=target,
                        success=result.success,
                        data=result.data,
                        error=result.error,
                        execution_time=result.execution_time,
                        metadata=result.metadata,
                        timestamp=timestamp
                    )
                    db_result.save()

                    # Store contact intelligence in graph database
                    self._ingest_contacts(target, tool_name, result.data)

                    return result
                except Exception as e:
                    logger.error(f"Tool {tool_name} failed: {e}")
                    session.results[tool_name] = {'error': str(e)}
                    
                    # Save error to database
                    from datetime import datetime
                    db_result = DBToolResult(
                        session_id=session_id,
                        tool_name=tool_name,
                        target=target,
                        success=False,
                        error=str(e),
                        execution_time=0.0,
                        timestamp=datetime.now()
                    )
                    db_result.save()
                    
                    return None
        
        # Execute all tools
        tasks = [run_tool(tool_name) for tool_name in execution_plan]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results with AI if enabled
        if self.ai_pilot and results:
            analysis = await self.ai_pilot.analyze_results(target, session.results)
            session.results['ai_analysis'] = analysis
            
            # Save AI analysis to database
            if isinstance(analysis, dict):
                ai_analysis = AIAnalysis(
                    session_id=session_id,
                    target=target,
                    summary=analysis.get('summary'),
                    key_findings=analysis.get('key_findings', []),
                    recommendations=analysis.get('recommendations', []),
                    risk_level=analysis.get('risk_level'),
                    interesting_targets=analysis.get('interesting_targets', []),
                    analysis_data=analysis
                )
                ai_analysis.save()

        # Derive business intelligence from main site web scrapers
        business_data = self._collect_main_site_data(session.results)
        if self.ai_pilot and business_data:
            business_profile = await self.ai_pilot.analyze_business_profile(target, business_data)
            if business_profile:
                session.results['business_profile'] = business_profile
                profile_record = BusinessProfile(
                    session_id=session_id,
                    target=target,
                    business_size=business_profile.get('business_size'),
                    incorporation_date=business_profile.get('incorporation_date'),
                    locations=business_profile.get('locations', []),
                    industry=business_profile.get('industry'),
                    other_insights=business_profile.get('other_insights', []),
                    source_tools=[item['tool'] for item in business_data if 'tool' in item],
                    analysis_data=business_profile,
                )
                profile_record.save()
        
        # Update session in database
        db_session = Session.get_by_session_id(session_id)
        if db_session:
            db_session.tools_executed = session.tools_executed
            db_session.complete()
        
        # Save session to JSON as backup
        session.status = "completed"
        await self._save_session(session)
        
        return session
    
    async def _save_session(self, session: ReconSession):
        """Save session results to disk"""
        session_file = self.results_dir / f"{session.session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session.to_dict(), f, indent=2)
        logger.info(f"Session saved to {session_file}")
    
    def get_session(self, session_id: str) -> Optional[ReconSession]:
        """Retrieve a session by ID from database"""
        # Try to get from memory first
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        # Load from database
        db_session = Session.get_by_session_id(session_id)
        if not db_session:
            return None
        
        # Get target
        db = get_db()
        target_row = db.fetchone("SELECT target FROM targets WHERE id = ?", (db_session.target_id,))
        if not target_row:
            return None
        
        target = target_row['target']
        
        # Get tool results
        tool_results = DBToolResult.get_by_session(session_id)
        results = {}
        for tr in tool_results:
            results[tr.tool_name] = {
                'success': tr.success,
                'data': tr.data,
                'error': tr.error,
                'execution_time': tr.execution_time,
                'metadata': tr.metadata,
                'timestamp': tr.timestamp.isoformat() if tr.timestamp else None
            }
        
        # Get AI analysis
        ai_analysis = AIAnalysis.get_by_session(session_id)
        if ai_analysis:
            results['ai_analysis'] = ai_analysis.analysis_data

        business_profile = BusinessProfile.get_by_session(session_id)
        if business_profile:
            results['business_profile'] = business_profile.analysis_data
        
        # Reconstruct session
        session = ReconSession(
            target=target,
            session_id=session_id,
            start_time=db_session.start_time,
            tools_executed=db_session.tools_executed,
            results=results,
            status=db_session.status
        )
        
        return session
    
    def _detect_target_type(self, target: str) -> str:
        """Detect target type"""
        if '@' in target:
            return 'email'
        elif target.replace('.', '').replace(':', '').isdigit() or ':' in target:
            return 'ip'
        elif '.' in target:
            return 'domain'
        else:
            return 'username'

    def _ingest_contacts(self, target: str, tool_name: str, data: Any):
        """Push contact-focused tool output into the graph database."""
        if not self.graph_db or not data or not isinstance(data, dict):
            return

        emails = data.get('emails')
        phones = data.get('phones')
        if emails or phones:
            try:
                self.graph_db.ingest_contacts(
                    target=target,
                    emails=emails,
                    phones=phones,
                    source=tool_name,
                )
            except Exception as exc:
                logger.debug("Skipping graph ingestion for %s: %s", tool_name, exc)

    def list_tools(self) -> List[str]:
        """List all available tools"""
        return list(self.tools.keys())
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict]:
        """Get information about a specific tool"""
        if tool_name in self.tools:
            tool = self.tools[tool_name]
            return {
                'name': tool.name,
                'description': tool.description,
                'category': tool.category,
                'requires_auth': tool.requires_auth
            }
        return None

    def _collect_main_site_data(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect data from web-category tools to feed into business profiling."""

        main_site_data: List[Dict[str, Any]] = []
        for tool_name, result in results.items():
            if tool_name in {'ai_analysis', 'business_profile'}:
                continue

            tool = self.tools.get(tool_name)
            if not tool or getattr(tool, 'category', None) != 'web':
                continue

            if isinstance(result, dict) and result.get('success') and result.get('data'):
                trimmed_data = self._trim_data(result.get('data'))
                main_site_data.append({'tool': tool_name, 'data': trimmed_data})

        return main_site_data

    def _trim_data(self, data: Any, max_items: int = 50) -> Any:
        """Trim large datasets before sending to the AI model."""

        if isinstance(data, list):
            return data[:max_items]
        if isinstance(data, dict):
            trimmed = {}
            for key, value in data.items():
                trimmed[key] = self._trim_data(value, max_items)
            return trimmed
        return data

