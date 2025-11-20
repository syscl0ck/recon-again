"""
Free API-based reconnaissance tools
No installation required, just API calls
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import quote

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class CrtShTool(BaseTool):
    """
    crt.sh certificate transparency search
    Free API, no auth required
    """
    
    @property
    def name(self) -> str:
        return "crt_sh"
    
    @property
    def description(self) -> str:
        return "Search certificate transparency logs for subdomains via crt.sh"
    
    @property
    def category(self) -> str:
        return "dns"
    
    async def run(self, target: str) -> ToolResult:
        """Query crt.sh for certificates"""
        import time
        start_time = time.time()
        
        try:
            # Remove protocol if present
            domain = target.replace('https://', '').replace('http://', '').split('/')[0]
            
            url = f"https://crt.sh/?q=%.{quote(domain)}&output=json"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract unique subdomains
                        subdomains = set()
                        for cert in data:
                            name_value = cert.get('name_value', '')
                            # Split by newlines and commas
                            for name in name_value.replace('\n', ',').split(','):
                                name = name.strip().lower()
                                if name and domain in name:
                                    # Remove wildcards
                                    name = name.replace('*.', '')
                                    if name.startswith('.'):
                                        name = name[1:]
                                    subdomains.add(name)
                        
                        subdomains = sorted(list(subdomains))
                        
                        execution_time = time.time() - start_time
                        return self._create_result(
                            target=target,
                            success=True,
                            data={'subdomains': subdomains, 'count': len(subdomains)},
                            execution_time=execution_time,
                            metadata={'source': 'crt.sh', 'certificates_found': len(data)}
                        )
                    else:
                        execution_time = time.time() - start_time
                        return self._create_result(
                            target=target,
                            success=False,
                            error=f"HTTP {response.status}",
                            execution_time=execution_time
                        )
        except asyncio.TimeoutError:
            return self._create_result(
                target=target,
                success=False,
                error="Request timeout"
            )
        except Exception as e:
            logger.error(f"crt.sh error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )


class UrlscanTool(BaseTool):
    """
    urlscan.io API integration
    Free tier available, no auth required for basic searches
    """
    
    @property
    def name(self) -> str:
        return "urlscan"
    
    @property
    def description(self) -> str:
        return "Search urlscan.io for historical scans and related domains"
    
    @property
    def category(self) -> str:
        return "web"
    
    async def run(self, target: str) -> ToolResult:
        """Search urlscan.io"""
        import time
        start_time = time.time()
        
        try:
            domain = target.replace('https://', '').replace('http://', '').split('/')[0]
            
            # Search for scans
            search_url = f"https://urlscan.io/api/v1/search/?q=domain:{domain}&size=100"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    search_url,
                    headers={'User-Agent': 'recon-again/0.1.0'},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        
                        # Extract unique domains and URLs
                        domains = set()
                        urls = set()
                        
                        for result in results:
                            page = result.get('page', {})
                            domain_found = page.get('domain', '')
                            url_found = page.get('url', '')
                            
                            if domain_found:
                                domains.add(domain_found)
                            if url_found:
                                urls.add(url_found)
                        
                        execution_time = time.time() - start_time
                        return self._create_result(
                            target=target,
                            success=True,
                            data={
                                'domains': sorted(list(domains)),
                                'urls': sorted(list(urls)),
                                'scan_count': len(results)
                            },
                            execution_time=execution_time,
                            metadata={'source': 'urlscan.io'}
                        )
                    else:
                        execution_time = time.time() - start_time
                        return self._create_result(
                            target=target,
                            success=False,
                            error=f"HTTP {response.status}",
                            execution_time=execution_time
                        )
        except Exception as e:
            logger.error(f"urlscan.io error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )


class HIBPTool(BaseTool):
    """
    Have I Been Pwned API integration
    Free API, requires API key for higher rate limits
    """
    
    @property
    def name(self) -> str:
        return "hibp"
    
    @property
    def description(self) -> str:
        return "Check if email/domain has been involved in data breaches via Have I Been Pwned"
    
    @property
    def category(self) -> str:
        return "breach"
    
    @property
    def requires_auth(self) -> bool:
        return False  # Can work without API key, but rate limited
    
    async def run(self, target: str) -> ToolResult:
        """Check HIBP for breaches"""
        import time
        import hashlib
        start_time = time.time()
        
        try:
            # HIBP API key from config (optional)
            api_key = self.config.get('hibp', {}).get('api_key')
            headers = {'User-Agent': 'recon-again/0.1.0'}
            if api_key:
                headers['hibp-api-key'] = api_key
            
            # Check if target is email or domain
            if '@' in target:
                # Email check
                email = target.lower().strip()
                sha1_hash = hashlib.sha1(email.encode()).hexdigest().upper()
                prefix = sha1_hash[:5]
                suffix = sha1_hash[5:]
                
                url = f"https://api.pwnedpasswords.com/range/{prefix}"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            text = await response.text()
                            # Check if suffix is in response
                            breached = suffix in text
                            
                            # Also check breach database
                            breach_url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote(email)}"
                            breaches = []
                            
                            if api_key:  # Only if we have API key
                                async with session.get(
                                    breach_url,
                                    headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=10)
                                ) as breach_response:
                                    if breach_response.status == 200:
                                        breaches = await breach_response.json()
                            
                            execution_time = time.time() - start_time
                            return self._create_result(
                                target=target,
                                success=True,
                                data={
                                    'breached': breached,
                                    'breaches': breaches,
                                    'breach_count': len(breaches)
                                },
                                execution_time=execution_time,
                                metadata={'source': 'haveibeenpwned.com'}
                            )
                        else:
                            execution_time = time.time() - start_time
                            return self._create_result(
                                target=target,
                                success=False,
                                error=f"HTTP {response.status}",
                                execution_time=execution_time
                            )
            else:
                # Domain check (requires API key)
                domain = target.replace('https://', '').replace('http://', '').split('/')[0]
                
                if not api_key:
                    return self._create_result(
                        target=target,
                        success=False,
                        error="Domain check requires HIBP API key"
                    )
                
                url = f"https://haveibeenpwned.com/api/v3/breaches?domain={quote(domain)}"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            breaches = await response.json()
                            execution_time = time.time() - start_time
                            return self._create_result(
                                target=target,
                                success=True,
                                data={
                                    'breaches': breaches,
                                    'breach_count': len(breaches)
                                },
                                execution_time=execution_time,
                                metadata={'source': 'haveibeenpwned.com'}
                            )
                        else:
                            execution_time = time.time() - start_time
                            return self._create_result(
                                target=target,
                                success=False,
                                error=f"HTTP {response.status}",
                                execution_time=execution_time
                            )
        except Exception as e:
            logger.error(f"HIBP error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )

