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
            
            # Run dnsrecon with std type (includes SOA, NS, A, AAAA, MX, SRV)
            # Use stdout capture instead of JSON file for better reliability
            cmd = ['dnsrecon', '-d', domain, '-t', 'std']
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            # Parse results from stdout
            # Format: [*] 	 TYPE value1 value2 ...
            records = []
            if stdout:
                output_lines = stdout.decode('utf-8', errors='ignore').split('\n')
                for line in output_lines:
                    line = line.strip()
                    # Skip empty lines, headers, and summary lines
                    if not line or line.startswith('[*] std:') or line.startswith('[-]') or \
                       line.startswith('[+]') and 'Records Found' in line or \
                       line.startswith('Enumerating'):
                        continue
                    
                    # Parse DNSRecon output format: [*] 	 TYPE value1 value2 ...
                    if line.startswith('[*]'):
                        parts = line.split()
                        if len(parts) >= 3:
                            try:
                                record_type = parts[1]
                                if record_type in ['SOA', 'NS', 'A', 'AAAA', 'MX', 'SRV', 'TXT', 'CNAME']:
                                    record = {
                                        'type': record_type,
                                        'raw': line,
                                        'values': parts[2:]  # All values after type
                                    }
                                    # For A records, first value is domain, second is IP
                                    if record_type == 'A' and len(parts) >= 4:
                                        record['domain'] = parts[2]
                                        record['ip'] = parts[3]
                                    # For NS/SOA, first value is hostname, second might be IP
                                    elif record_type in ['NS', 'SOA'] and len(parts) >= 3:
                                        record['hostname'] = parts[2]
                                        if len(parts) >= 4:
                                            record['ip'] = parts[3]
                                    # For TXT, combine all values
                                    elif record_type == 'TXT':
                                        record['domain'] = parts[2] if len(parts) > 2 else domain
                                        record['text'] = ' '.join(parts[3:]) if len(parts) > 3 else ''
                                    
                                    records.append(record)
                            except Exception as e:
                                logger.debug(f"Failed to parse DNSRecon line: {line}, error: {e}")
                                pass
            
            # Also try JSON output as fallback
            if not records:
                output_file = Path('/tmp/dnsrecon_output.json')
                if output_file.exists():
                    with open(output_file, 'r') as f:
                        content = f.read()
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
        import aiohttp
        from urllib.parse import quote
        start_time = time.time()
        
        try:
            domain = target.replace('https://', '').replace('http://', '').split('/')[0]
            urls = []
            
            # Try waybackpy first (already installed)
            try:
                import waybackpy
                wayback = waybackpy.Url(domain)
                # Get recent snapshots
                urls_data = wayback.near(year=2023, month=1)
                urls = [url.url for url in urls_data]
                logger.info(f"Waybackpy found {len(urls)} URLs")
            except Exception as e:
                logger.debug(f"waybackpy failed: {e}, trying direct API")
            
            # Fallback to direct Wayback Machine API
            if not urls:
                try:
                    api_url = f"https://web.archive.org/cdx/search/cdx?url={quote(domain)}/*&output=json&collapse=urlkey&limit=1000"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            api_url,
                            timeout=aiohttp.ClientTimeout(total=30),
                            headers={'User-Agent': 'recon-again/0.1.0'}
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                if data and len(data) > 1:
                                    # First row is headers, skip it
                                    # Format: [timestamp, original, url, ...]
                                    urls = [row[2] for row in data[1:] if len(row) > 2 and row[2]]
                                    # Remove duplicates
                                    urls = list(set(urls))
                                    logger.info(f"Wayback API found {len(urls)} URLs")
                except Exception as e:
                    logger.error(f"Wayback API call failed: {e}")
            
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
            # Skip if target looks like a domain (contains dots and no @)
            if '.' in target and '@' not in target:
                return self._create_result(
                    target=target,
                    success=False,
                    error="Sherlock is for username enumeration, not domains. Use a username as target.",
                    execution_time=0.0
                )
            
            username = target.replace('@', '').strip()
            
            # Check if sherlock is available (try multiple paths)
            sherlock_path = None
            possible_paths = [
                'sherlock',
                '/usr/local/bin/sherlock',
                '/opt/sherlock/sherlock_project/sherlock.py',
                '/opt/sherlock/sherlock_project/__main__.py',
                'python3 /opt/sherlock/sherlock_project/sherlock.py',
                'python3 -m sherlock_project.sherlock'
            ]
            
            for path in possible_paths:
                try:
                    if path.startswith('python3'):
                        # Test if Python script exists
                        if ' -m ' in path:
                            # Module path
                            result = subprocess.run(
                                path.split() + ['--version'],
                                capture_output=True,
                                timeout=5
                            )
                            if result.returncode == 0 or result.returncode == 2:  # 2 is help/version exit
                                sherlock_path = path
                                break
                        else:
                            # Script path
                            script_path = path.split()[-1]
                            if Path(script_path).exists():
                                sherlock_path = path
                                break
                    else:
                        result = subprocess.run(
                            [path, '--version'] if path != 'sherlock' else ['sherlock', '--version'],
                            capture_output=True,
                            timeout=5
                        )
                        # Exit code 2 often means help/version was shown
                        if result.returncode in [0, 2] or 'sherlock' in result.stderr.decode('utf-8', errors='ignore').lower():
                            sherlock_path = path
                            break
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
            
            if not sherlock_path:
                return self._create_result(
                    target=target,
                    success=False,
                    error="Sherlock not installed. Install from: https://github.com/sherlock-project/sherlock"
                )
            
            # Run sherlock - use module approach or direct Python execution
            output_file = Path(f'/tmp/sherlock_{username}.json')
            
            # Prefer module execution if available, otherwise use direct script
            if '/opt/sherlock' in str(sherlock_path) or not sherlock_path:
                # Use module execution (most reliable)
                cmd = [
                    'python3', '-m', 'sherlock_project.sherlock',
                    '--json',
                    '--output', str(output_file),
                    '--timeout', '10',
                    '--print-found',
                    username
                ]
            elif sherlock_path.startswith('python3'):
                if ' -m ' in sherlock_path:
                    cmd = sherlock_path.split() + [
                        '--json',
                        '--output', str(output_file),
                        '--timeout', '10',
                        '--print-found',
                        username
                    ]
                else:
                    script_path = sherlock_path.split()[-1]
                    cmd = [
                        'python3',
                        script_path,
                        '--json',
                        '--output', str(output_file),
                        '--timeout', '10',
                        '--print-found',
                        username
                    ]
            else:
                cmd = [
                    sherlock_path,
                    '--json',
                    '--output', str(output_file),
                    '--timeout', '10',
                    '--print-found',
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


class TheHarvesterTool(BaseTool):
    """
    theHarvester passive email and subdomain harvesting
    Passive tool, no API keys required
    """
    
    @property
    def name(self) -> str:
        return "theharvester"
    
    @property
    def description(self) -> str:
        return "Passive email and subdomain harvesting using theHarvester"
    
    @property
    def category(self) -> str:
        return "osint"
    
    async def run(self, target: str) -> ToolResult:
        """Run theHarvester"""
        import time
        start_time = time.time()
        
        try:
            domain = target.replace('https://', '').replace('http://', '').split('/')[0]
            
            # Run theHarvester with passive sources only
            # Try different command variations
            # -b: sources (all, baidu, bing, etc.)
            # -d: domain
            # -f: output file
            output_file = Path('/tmp/theharvester_output.xml')
            # Try different command variations
            cmd_variations = [
                ['theHarvester', '-d', domain, '-b', 'all', '-f', str(output_file), '-l', '500'],
                ['theharvester', '-d', domain, '-b', 'all', '-f', str(output_file), '-l', '500'],
                ['python3', '-m', 'theHarvester', '-d', domain, '-b', 'all', '-f', str(output_file), '-l', '500'],
            ]
            
            process = None
            for cmd in cmd_variations:
                try:
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    break
                except FileNotFoundError:
                    continue
            
            if process is None:
                return self._create_result(
                    target=target,
                    success=False,
                    error="theHarvester not found. Install with: pip install theHarvester"
                )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            # Check return code
            return_code = await process.wait()
            
            # Parse results
            emails = []
            hosts = []
            ips = []
            
            # Also check stdout for results (theHarvester might output to stdout)
            stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ''
            stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ''
            
            # Extract emails from stdout/stderr as fallback
            if stdout_text:
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                found_emails = re.findall(email_pattern, stdout_text)
                emails.extend(found_emails)
            
            if output_file.exists():
                # Parse XML output
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(output_file)
                    root = tree.getroot()
                    
                    # Extract emails
                    for email in root.findall('.//email'):
                        if email.text:
                            emails.append(email.text.strip())
                    
                    # Extract hosts
                    for host in root.findall('.//host'):
                        if host.text:
                            hosts.append(host.text.strip())
                    
                    # Extract IPs
                    for ip in root.findall('.//ip'):
                        if ip.text:
                            ips.append(ip.text.strip())
                except Exception as e:
                    logger.debug(f"XML parsing failed: {e}, trying text parsing")
                    # Fallback to text parsing
                    try:
                        with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Extract emails
                            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                            found_emails = re.findall(email_pattern, content)
                            emails.extend(found_emails)
                            # Extract hosts/domains
                            host_pattern = r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
                            found_hosts = re.findall(host_pattern, content)
                            hosts.extend([h for h in found_hosts if domain in h])
                    except Exception as parse_error:
                        logger.debug(f"Text parsing also failed: {parse_error}")
                
                try:
                    output_file.unlink()
                except:
                    pass
            
            execution_time = time.time() - start_time
            
            # Clean and deduplicate
            emails = list(set([e.lower() for e in emails if e and '@' in e]))
            hosts = list(set([h for h in hosts if h]))
            ips = list(set([ip for ip in ips if ip]))
            
            if emails or hosts or ips:
                return self._create_result(
                    target=target,
                    success=True,
                    data={
                        'emails': emails,
                        'hosts': hosts,
                        'ips': ips,
                        'email_count': len(emails),
                        'host_count': len(hosts),
                        'ip_count': len(ips)
                    },
                    execution_time=execution_time,
                    metadata={'source': 'theHarvester', 'return_code': return_code}
                )
            else:
                error_msg = "No results found"
                if stderr_text:
                    error_msg += f" (stderr: {stderr_text[:200]})"
                return self._create_result(
                    target=target,
                    success=False,
                    error=error_msg,
                    execution_time=execution_time
                )
        except asyncio.TimeoutError:
            return self._create_result(
                target=target,
                success=False,
                error="Tool execution timeout"
            )
        except Exception as e:
            logger.error(f"theHarvester error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )


class GauTool(BaseTool):
    """
    gau (Get All URLs) - Extract URLs from common sources
    Passive tool, no API keys required
    """
    
    @property
    def name(self) -> str:
        return "gau"
    
    @property
    def description(self) -> str:
        return "Extract URLs from common sources using gau"
    
    @property
    def category(self) -> str:
        return "web"
    
    async def run(self, target: str) -> ToolResult:
        """Run gau"""
        import time
        start_time = time.time()
        
        try:
            domain = target.replace('https://', '').replace('http://', '').split('/')[0]
            
            # Run gau - try to run directly, will catch FileNotFoundError if not available
            cmd = ['gau', domain, '--subs']
            
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            except FileNotFoundError:
                return self._create_result(
                    target=target,
                    success=False,
                    error="gau not installed. Install from: https://github.com/lc/gau"
                )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            # Parse results
            urls = []
            if stdout:
                urls = [line.strip().decode() for line in stdout.split(b'\n') if line.strip()]
                urls = list(set(urls))  # Remove duplicates
            
            execution_time = time.time() - start_time
            
            if urls:
                return self._create_result(
                    target=target,
                    success=True,
                    data={'urls': urls, 'count': len(urls)},
                    execution_time=execution_time,
                    metadata={'source': 'gau'}
                )
            else:
                return self._create_result(
                    target=target,
                    success=False,
                    error="No URLs found or tool execution failed",
                    execution_time=execution_time
                )
        except asyncio.TimeoutError:
            return self._create_result(
                target=target,
                success=False,
                error="Tool execution timeout"
            )
        except Exception as e:
            logger.error(f"gau error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )


class HoleheTool(BaseTool):
    """
    Holehe - Email account existence checker
    Passive tool, no API keys required
    """
    
    @property
    def name(self) -> str:
        return "holehe"
    
    @property
    def description(self) -> str:
        return "Check if email accounts exist on various platforms using Holehe"
    
    @property
    def category(self) -> str:
        return "osint"
    
    async def run(self, target: str) -> ToolResult:
        """Run Holehe"""
        import time
        start_time = time.time()
        
        try:
            # Extract email (remove @ if present, but Holehe needs full email)
            if '@' not in target:
                return self._create_result(
                    target=target,
                    success=False,
                    error="Holehe requires an email address as target"
                )
            
            email = target.strip()
            
            # Check if holehe is available
            try:
                result = subprocess.run(
                    ['holehe', '--version'],
                    capture_output=True,
                    timeout=5
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # Try Python module
                try:
                    import holehe
                except ImportError:
                    return self._create_result(
                        target=target,
                        success=False,
                        error="Holehe not installed. Install with: pip install holehe"
                    )
            
            # Run holehe
            # Try CLI first, then Python module
            findings = []
            
            try:
                # CLI approach
                cmd = ['holehe', email, '--only-used']
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
                    output = stdout.decode('utf-8', errors='ignore')
                    # Parse output - format: [*] platform: exists/not exists
                    for line in output.split('\n'):
                        if '[*]' in line or '[+]' in line:
                            parts = line.split(':')
                            if len(parts) >= 2:
                                platform = parts[0].replace('[*]', '').replace('[+]', '').strip()
                                status = parts[1].strip()
                                if 'exists' in status.lower() or 'used' in status.lower():
                                    findings.append({
                                        'platform': platform,
                                        'status': 'exists',
                                        'raw': line.strip()
                                    })
            except Exception as e:
                logger.debug(f"Holehe CLI failed: {e}, trying Python module")
                # Python module approach
                try:
                    import holehe
                    results = holehe.find(email)
                    for result in results:
                        if result.get('exists', False):
                            findings.append({
                                'platform': result.get('name', 'unknown'),
                                'status': 'exists',
                                'email': email
                            })
                except Exception as e2:
                    logger.error(f"Holehe Python module failed: {e2}")
            
            execution_time = time.time() - start_time
            
            if findings:
                return self._create_result(
                    target=target,
                    success=True,
                    data={'findings': findings, 'count': len(findings)},
                    execution_time=execution_time,
                    metadata={'source': 'holehe'}
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
            logger.error(f"Holehe error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )


class MaigretTool(BaseTool):
    """
    Maigret - Username enumeration across platforms
    Passive tool, no API keys required
    """
    
    @property
    def name(self) -> str:
        return "maigret"
    
    @property
    def description(self) -> str:
        return "Username enumeration across social platforms using Maigret"
    
    @property
    def category(self) -> str:
        return "osint"
    
    async def run(self, target: str) -> ToolResult:
        """Run Maigret"""
        import time
        start_time = time.time()
        
        try:
            # Extract username (remove @ if present)
            username = target.replace('@', '').strip()
            
            # Skip if target looks like a domain
            if '.' in target and '@' not in target:
                return self._create_result(
                    target=target,
                    success=False,
                    error="Maigret is for username enumeration, not domains. Use a username as target.",
                    execution_time=0.0
                )
            
            # Check if maigret is available
            try:
                result = subprocess.run(
                    ['maigret', '--version'],
                    capture_output=True,
                    timeout=5
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # Try Python module
                try:
                    import maigret
                except ImportError:
                    return self._create_result(
                        target=target,
                        success=False,
                        error="Maigret not installed. Install with: pip install maigret"
                    )
            
            # Run maigret
            output_file = Path(f'/tmp/maigret_{username}.json')
            cmd = [
                'maigret',
                username,
                '--print-found',
                '--json',
                '--output', str(output_file),
                '--timeout', '10'
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
                    metadata={'source': 'maigret'}
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
            logger.error(f"Maigret error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )


class ArjunTool(BaseTool):
    """
    Arjun - HTTP parameter discovery
    Passive tool, no API keys required
    """
    
    @property
    def name(self) -> str:
        return "arjun"
    
    @property
    def description(self) -> str:
        return "HTTP parameter discovery using Arjun"
    
    @property
    def category(self) -> str:
        return "web"
    
    async def run(self, target: str) -> ToolResult:
        """Run Arjun"""
        import time
        start_time = time.time()
        
        try:
            # Ensure target has protocol
            if not target.startswith(('http://', 'https://')):
                target = f"https://{target}"
            
            # Check if arjun is available
            try:
                result = subprocess.run(
                    ['arjun', '--version'],
                    capture_output=True,
                    timeout=5
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # Try Python module
                try:
                    import arjun
                except ImportError:
                    return self._create_result(
                        target=target,
                        success=False,
                        error="Arjun not installed. Install with: pip install arjun"
                    )
            
            # Run arjun
            output_file = Path('/tmp/arjun_output.json')
            cmd = [
                'arjun',
                '-u', target,
                '--json',
                '-o', str(output_file),
                '--timeout', '10',
                '--passive'  # Passive mode only
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
            parameters = []
            if output_file.exists():
                with open(output_file, 'r') as f:
                    try:
                        data = json.load(f)
                        if isinstance(data, dict):
                            parameters = data.get('params', [])
                        elif isinstance(data, list):
                            parameters = data
                    except json.JSONDecodeError:
                        pass
                output_file.unlink()
            
            execution_time = time.time() - start_time
            
            if parameters:
                return self._create_result(
                    target=target,
                    success=True,
                    data={'parameters': parameters, 'count': len(parameters)},
                    execution_time=execution_time,
                    metadata={'source': 'arjun'}
                )
            else:
                return self._create_result(
                    target=target,
                    success=False,
                    error="No parameters found or tool execution failed",
                    execution_time=execution_time
                )
        except asyncio.TimeoutError:
            return self._create_result(
                target=target,
                success=False,
                error="Tool execution timeout"
            )
        except Exception as e:
            logger.error(f"Arjun error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )


class EmailHarvesterTool(BaseTool):
    """
    EmailHarvester - Email address discovery
    Passive tool, no API keys required
    """
    
    @property
    def name(self) -> str:
        return "emailharvester"
    
    @property
    def description(self) -> str:
        return "Email address discovery using EmailHarvester"
    
    @property
    def category(self) -> str:
        return "osint"
    
    async def run(self, target: str) -> ToolResult:
        """Run EmailHarvester"""
        import time
        start_time = time.time()
        
        try:
            domain = target.replace('https://', '').replace('http://', '').split('/')[0]
            
            # Check if EmailHarvester is available
            # EmailHarvester is typically a Python script
            emailharvester_paths = [
                'emailHarvester',
                'EmailHarvester',
                'emailharvester',
                '/usr/local/bin/emailHarvester',
                '/opt/EmailHarvester/emailHarvester.py'
            ]
            
            emailharvester_path = None
            for path in emailharvester_paths:
                try:
                    if path.endswith('.py'):
                        if Path(path).exists():
                            emailharvester_path = path
                            break
                    else:
                        result = subprocess.run(
                            [path, '--help'],
                            capture_output=True,
                            timeout=5
                        )
                        if result.returncode in [0, 2]:
                            emailharvester_path = path
                            break
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
            
            if not emailharvester_path:
                # Try Python module
                try:
                    import emailHarvester
                    emailharvester_path = 'python_module'
                except ImportError:
                    return self._create_result(
                        target=target,
                        success=False,
                        error="EmailHarvester not installed. Install from: https://github.com/maldevel/EmailHarvester"
                    )
            
            # Run EmailHarvester
            emails = []
            
            if emailharvester_path == 'python_module':
                # Use Python module
                try:
                    import emailHarvester
                    # EmailHarvester typically searches Google, Bing, etc.
                    # This is a simplified version
                    emails = []  # Would need to implement module usage
                except Exception as e:
                    logger.error(f"EmailHarvester module error: {e}")
            else:
                # Use CLI
                if emailharvester_path.endswith('.py'):
                    cmd = ['python3', emailharvester_path, '-d', domain]
                else:
                    cmd = [emailharvester_path, '-d', domain]
                
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
                    output = stdout.decode('utf-8', errors='ignore')
                    # Parse email addresses from output
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    emails = list(set(re.findall(email_pattern, output)))
            
            execution_time = time.time() - start_time
            
            if emails:
                return self._create_result(
                    target=target,
                    success=True,
                    data={'emails': emails, 'count': len(emails)},
                    execution_time=execution_time,
                    metadata={'source': 'EmailHarvester'}
                )
            else:
                return self._create_result(
                    target=target,
                    success=False,
                    error="No emails found or tool execution failed",
                    execution_time=execution_time
                )
        except asyncio.TimeoutError:
            return self._create_result(
                target=target,
                success=False,
                error="Tool execution timeout"
            )
        except Exception as e:
            logger.error(f"EmailHarvester error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )

