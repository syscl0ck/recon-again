"""
AIPilot: OpenRouter integration for intelligent reconnaissance automation
Uses AI to plan tool execution, analyze results, and suggest next steps
"""

import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class AIPilot:
    """
    AI-powered pilot for intelligent recon automation
    Uses OpenRouter API to make smart decisions about tool execution
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AI Pilot with OpenRouter configuration
        
        Args:
            config: Configuration dict with api_key, model, base_url
        """
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'openai/gpt-4-turbo')
        self.base_url = config.get('base_url', 'https://openrouter.ai/api/v1')
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("AIPilot initialized without API key - AI features disabled")
    
    async def _call_openrouter(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """
        Make API call to OpenRouter
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            Response text or None if failed
        """
        if not self.enabled:
            return None
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/recon-again/recon-again',
            'X-Title': 'recon-again'
        }
        
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.base_url}/chat/completions',
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content']
                    else:
                        logger.error(f"OpenRouter API error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"OpenRouter API call failed: {e}")
            return None
    
    async def create_execution_plan(
        self,
        target: str,
        available_tools: List[str]
    ) -> List[str]:
        """
        Use AI to create an optimal tool execution plan
        
        Args:
            target: Target domain/IP/identifier
            available_tools: List of available tool names
            
        Returns:
            Ordered list of tools to execute
        """
        if not self.enabled:
            return available_tools[:5]  # Default: first 5 tools
        
        prompt = f"""You are an expert penetration tester planning reconnaissance for target: {target}

Available tools: {', '.join(available_tools)}

Create an optimal execution plan. Consider:
1. Start with passive, non-intrusive tools (APIs, DNS lookups)
2. Then move to active enumeration (subdomain discovery, port scanning)
3. Finally, deep analysis tools (vulnerability scanning, content discovery)

Respond with ONLY a JSON array of tool names in execution order, no other text.
Example: ["crt_sh", "urlscan", "sublist3r", "dnsrecon"]
"""
        
        messages = [
            {
                'role': 'system',
                'content': 'You are a cybersecurity expert specializing in reconnaissance. Provide concise, actionable tool execution plans.'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ]
        
        response = await self._call_openrouter(messages, temperature=0.3)
        
        if response:
            try:
                # Extract JSON from response (handle markdown code blocks)
                response = response.strip()
                if response.startswith('```'):
                    response = response.split('```')[1]
                    if response.startswith('json'):
                        response = response[4:]
                response = response.strip()
                
                plan = json.loads(response)
                if isinstance(plan, list):
                    # Validate tools exist
                    valid_plan = [t for t in plan if t in available_tools]
                    if valid_plan:
                        logger.info(f"AI created execution plan: {valid_plan}")
                        return valid_plan
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse AI response: {e}")
        
        # Fallback to default plan
        return available_tools[:5]
    
    async def analyze_results(
        self,
        target: str,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use AI to analyze recon results and provide insights
        
        Args:
            target: Target that was scanned
            results: Dictionary of tool results
            
        Returns:
            Analysis dict with insights, recommendations, and next steps
        """
        if not self.enabled:
            return {'status': 'ai_disabled'}
        
        # Summarize results for AI
        results_summary = {}
        for tool_name, tool_result in results.items():
            if isinstance(tool_result, dict) and 'error' not in tool_result:
                if 'data' in tool_result:
                    data = tool_result['data']
                    if isinstance(data, list):
                        results_summary[tool_name] = f"Found {len(data)} items"
                    elif isinstance(data, dict):
                        results_summary[tool_name] = f"Found {len(data)} keys"
                    else:
                        results_summary[tool_name] = str(data)[:200]
                else:
                    results_summary[tool_name] = "Completed"
        
        prompt = f"""Analyze reconnaissance results for target: {target}

Results summary:
{json.dumps(results_summary, indent=2)}

Provide analysis in JSON format with:
1. "summary": Brief overview of findings
2. "key_findings": Array of important discoveries
3. "recommendations": Array of next steps or tools to run
4. "risk_level": "low", "medium", "high", or "critical"
5. "interesting_targets": Array of subdomains/IPs worth investigating

Respond with ONLY valid JSON, no markdown or code blocks.
"""
        
        messages = [
            {
                'role': 'system',
                'content': 'You are a cybersecurity analyst. Analyze reconnaissance data and provide actionable insights in structured JSON format.'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ]
        
        response = await self._call_openrouter(messages, temperature=0.5)
        
        if response:
            try:
                # Extract JSON
                response = response.strip()
                if response.startswith('```'):
                    response = response.split('```')[1]
                    if response.startswith('json'):
                        response = response[4:]
                response = response.strip()
                
                analysis = json.loads(response)
                logger.info("AI analysis completed")
                return analysis
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse AI analysis: {e}")

        return {'status': 'analysis_failed'}

    async def analyze_business_profile(
        self,
        target: str,
        scraper_results: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Use OpenRouter to infer business details from main site scraper data."""

        if not self.enabled:
            return {'status': 'ai_disabled'}

        prompt = f"""
You are a business intelligence analyst. Using the scraped website data below, infer structured business details for {target}.
Focus on:
- "business_size": approximate employee count band or revenue band (e.g., "51-200 employees" or "~$10M revenue").
- "incorporation_date": earliest year or precise incorporation/formation date if visible.
- "locations": list of headquarters/offices/regions mentioned.
- "industry": concise description of what the business does.
- "other_insights": list up to 5 notable facts (products, markets, certifications, funding, leadership hints, etc.).

Scraper data:
{json.dumps(scraper_results, indent=2)}

Respond with ONLY valid JSON using these keys. Use null or empty arrays when unknown.
"""

        messages = [
            {
                'role': 'system',
                'content': 'You are a precise business analyst. Respond with compact JSON only.'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ]

        response = await self._call_openrouter(messages, temperature=0.2, max_tokens=800)
        if not response:
            return None

        try:
            cleaned = response.strip()
            if cleaned.startswith('```'):
                cleaned = cleaned.split('```')[1]
                if cleaned.startswith('json'):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            if isinstance(data, dict):
                # Ensure expected keys exist
                data.setdefault('business_size', None)
                data.setdefault('incorporation_date', None)
                data.setdefault('locations', [])
                data.setdefault('industry', None)
                data.setdefault('other_insights', [])
                return data
        except json.JSONDecodeError as exc:
            logger.warning(f"Failed to parse business profile response: {exc}")

        return None

