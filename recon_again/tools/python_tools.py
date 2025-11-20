"""
Python-based reconnaissance tools
These may require external dependencies or subprocess execution
"""

import asyncio
import subprocess
import logging
import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class Sublist3rTool(BaseTool):
    """
    Sublist3r subdomain enumeration
    Requires sublist3r to be installed: pip install sublist3r
    """
    
    @property
    def name(self) -> str:
        return "sublist3r"
    
    @property
    def description(self) -> str:
        return "Subdomain enumeration using Sublist3r"
    
    @property
    def category(self) -> str:
        return "dns"
    
    async def run(self, target: str) -> ToolResult:
        """Run Sublist3r"""
        import time
        start_time = time.time()
        
        try:
            domain = target.replace('https://', '').replace('http://', '').split('/')[0]
            
            # Check if sublist3r is available
            try:
                result = subprocess.run(
                    ['sublist3r', '--version'],
                    capture_output=True,
                    timeout=5
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # Try Python module instead
                try:
                    import sublist3r
                except ImportError:
                    return self._create_result(
                        target=target,
                        success=False,
                        error="Sublist3r not installed. Install with: pip install sublist3r"
                    )
            
            # Run sublist3r
            cmd = ['sublist3r', '-d', domain, '-o', '/tmp/sublist3r_output.txt', '-t', '10']
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            # Read results
            subdomains = []
            output_file = Path('/tmp/sublist3r_output.txt')
            if output_file.exists():
                with open(output_file, 'r') as f:
                    subdomains = [line.strip() for line in f if line.strip()]
                output_file.unlink()  # Clean up
            
            execution_time = time.time() - start_time
            
            if subdomains:
                return self._create_result(
                    target=target,
                    success=True,
                    data={'subdomains': subdomains, 'count': len(subdomains)},
                    execution_time=execution_time,
                    metadata={'source': 'sublist3r'}
                )
            else:
                return self._create_result(
                    target=target,
                    success=False,
                    error="No subdomains found or tool execution failed",
                    execution_time=execution_time
                )
        except asyncio.TimeoutError:
            return self._create_result(
                target=target,
                success=False,
                error="Tool execution timeout"
            )
        except Exception as e:
            logger.error(f"Sublist3r error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )


class DNSReconTool(BaseTool):
    """
    DNSRecon DNS enumeration
    Requires dnsrecon to be installed
    """
    
    @property
    def name(self) -> str:
        return "dnsrecon"
    
    @property
    def description(self) -> str:
        return "DNS enumeration and record discovery using DNSRecon"
    
    @property
    def category(self) -> str:
        return "dns"
    
    async def run(self, target: str) -> ToolResult:
        """Run DNSRecon"""
        import time
        start_time = time.time()
        
        try:
            domain = target.replace('https://', '').replace('http://', '').split('/')[0]
            
            # Check if dnsrecon is available
            try:
                result = subprocess.run(
                    ['dnsrecon', '-h'],
                    capture_output=True,
                    timeout=5
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return self._create_result(
                    target=target,
                    success=False,
                    error="DNSRecon not installed. Install with: pip install dnsrecon"
                )
            
            # Run dnsrecon
            cmd = ['dnsrecon', '-d', domain, '-t', 'std', '--json', '/tmp/dnsrecon_output.json']
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            # Parse results
            records = []
            output_file = Path('/tmp/dnsrecon_output.json')
            if output_file.exists():
                with open(output_file, 'r') as f:
                    content = f.read()
                    # DNSRecon outputs one JSON object per line
                    for line in content.strip().split('\n'):
                        if line.strip():
                            try:
                                records.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
                output_file.unlink()
            
            execution_time = time.time() - start_time
            
            if records:
                return self._create_result(
                    target=target,
                    success=True,
                    data={'records': records, 'count': len(records)},
                    execution_time=execution_time,
                    metadata={'source': 'dnsrecon'}
                )
            else:
                return self._create_result(
                    target=target,
                    success=False,
                    error="No DNS records found or tool execution failed",
                    execution_time=execution_time
                )
        except asyncio.TimeoutError:
            return self._create_result(
                target=target,
                success=False,
                error="Tool execution timeout"
            )
        except Exception as e:
            logger.error(f"DNSRecon error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )


class DirsearchTool(BaseTool):
    """
    Dirsearch directory/file brute-forcing
    Requires dirsearch to be installed
    """
    
    @property
    def name(self) -> str:
        return "dirsearch"
    
    @property
    def description(self) -> str:
        return "Directory and file brute-forcing using dirsearch"
    
    @property
    def category(self) -> str:
        return "web"
    
    async def run(self, target: str) -> ToolResult:
        """Run dirsearch"""
        import time
        start_time = time.time()
        
        try:
            # Ensure target has protocol
            if not target.startswith(('http://', 'https://')):
                target = f"https://{target}"
            
            # Check if dirsearch is available
            try:
                result = subprocess.run(
                    ['dirsearch', '--version'],
                    capture_output=True,
                    timeout=5
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return self._create_result(
                    target=target,
                    success=False,
                    error="Dirsearch not installed. Install from: https://github.com/maurosoria/dirsearch"
                )
            
            # Run dirsearch with limited wordlist for speed
            output_file = Path('/tmp/dirsearch_output.json')
            cmd = [
                'dirsearch',
                '-u', target,
                '-e', 'php,html,js,txt,json',
                '--json-report', str(output_file),
                '--quiet',
                '--threads', '10',
                '--max-time', '60'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            # Parse results
            findings = []
            if output_file.exists():
                with open(output_file, 'r') as f:
                    try:
                        data = json.load(f)
                        findings = data.get('results', [])
                    except json.JSONDecodeError:
                        pass
                output_file.unlink()
            
            execution_time = time.time() - start_time
            
            if findings:
                return self._create_result(
                    target=target,
                    success=True,
                    data={'findings': findings, 'count': len(findings)},
                    execution_time=execution_time,
                    metadata={'source': 'dirsearch'}
                )
            else:
                return self._create_result(
                    target=target,
                    success=False,
                    error="No directories/files found or tool execution failed",
                    execution_time=execution_time
                )
        except asyncio.TimeoutError:
            return self._create_result(
                target=target,
                success=False,
                error="Tool execution timeout"
            )
        except Exception as e:
            logger.error(f"Dirsearch error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )


class WaybackTool(BaseTool):
    """
    Wayback Machine URL extraction
    Uses waybackurls (Go tool) or waybackpy (Python)
    """
    
    @property
    def name(self) -> str:
        return "wayback"
    
    @property
    def description(self) -> str:
        return "Extract historical URLs from Wayback Machine"
    
    @property
    def category(self) -> str:
        return "web"
    
    async def run(self, target: str) -> ToolResult:
        """Extract Wayback URLs"""
        import time
        start_time = time.time()
        
        try:
            domain = target.replace('https://', '').replace('http://', '').split('/')[0]
            
            # Try waybackurls (Go tool) first
            waybackurls_available = False
            try:
                result = subprocess.run(
                    ['waybackurls', '-version'],
                    capture_output=True,
                    timeout=5
                )
                waybackurls_available = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            urls = []
            
            if waybackurls_available:
                # Use waybackurls
                cmd = ['waybackurls', domain]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
                
                if stdout:
                    urls = [line.strip().decode() for line in stdout.split(b'\n') if line.strip()]
            else:
                # Fallback to waybackpy or direct API
                try:
                    import waybackpy
                    wayback = waybackpy.Url(domain)
                    urls_data = wayback.near(year=2020, month=1)
                    urls = [url.url for url in urls_data]
                except ImportError:
                    # Direct API call
                    import aiohttp
                    api_url = f"http://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&collapse=urlkey"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                            if response.status == 200:
                                data = await response.json()
                                if data and len(data) > 1:
                                    # First row is headers, skip it
                                    urls = [row[2] for row in data[1:] if len(row) > 2]
            
            execution_time = time.time() - start_time
            
            if urls:
                return self._create_result(
                    target=target,
                    success=True,
                    data={'urls': urls, 'count': len(urls)},
                    execution_time=execution_time,
                    metadata={'source': 'wayback_machine'}
                )
            else:
                return self._create_result(
                    target=target,
                    success=False,
                    error="No URLs found in Wayback Machine",
                    execution_time=execution_time
                )
        except asyncio.TimeoutError:
            return self._create_result(
                target=target,
                success=False,
                error="Tool execution timeout"
            )
        except Exception as e:
            logger.error(f"Wayback error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )


class SherlockTool(BaseTool):
    """
    Sherlock username enumeration across social platforms
    Requires sherlock to be installed
    """
    
    @property
    def name(self) -> str:
        return "sherlock"
    
    @property
    def description(self) -> str:
        return "Username enumeration across social media platforms using Sherlock"
    
    @property
    def category(self) -> str:
        return "osint"
    
    async def run(self, target: str) -> ToolResult:
        """Run Sherlock"""
        import time
        start_time = time.time()
        
        try:
            # Extract username (remove @ if present)
            username = target.replace('@', '').strip()
            
            # Check if sherlock is available
            try:
                result = subprocess.run(
                    ['sherlock', '--version'],
                    capture_output=True,
                    timeout=5
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return self._create_result(
                    target=target,
                    success=False,
                    error="Sherlock not installed. Install from: https://github.com/sherlock-project/sherlock"
                )
            
            # Run sherlock
            output_file = Path(f'/tmp/sherlock_{username}.json')
            cmd = [
                'sherlock',
                '--json',
                '--output', str(output_file),
                '--timeout', '10',
                username
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            # Parse results
            findings = []
            if output_file.exists():
                with open(output_file, 'r') as f:
                    try:
                        data = json.load(f)
                        findings = data
                    except json.JSONDecodeError:
                        pass
                output_file.unlink()
            
            execution_time = time.time() - start_time
            
            if findings:
                return self._create_result(
                    target=target,
                    success=True,
                    data={'findings': findings, 'count': len(findings)},
                    execution_time=execution_time,
                    metadata={'source': 'sherlock'}
                )
            else:
                return self._create_result(
                    target=target,
                    success=False,
                    error="No accounts found or tool execution failed",
                    execution_time=execution_time
                )
        except asyncio.TimeoutError:
            return self._create_result(
                target=target,
                success=False,
                error="Tool execution timeout"
            )
        except Exception as e:
            logger.error(f"Sherlock error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )

