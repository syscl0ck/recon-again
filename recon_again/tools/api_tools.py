"""
Free API-based reconnaissance tools
No installation required, just API calls
"""

import aiohttp
import asyncio
import logging
import re
from typing import Dict, Any, List, Optional
from urllib.parse import quote

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class CloudEnumTool(BaseTool):
    """
    Lightweight cloud resource discovery

    Probes common object storage providers (AWS S3, GCP Storage, Azure Blob)
    using likely bucket names derived from the target.
    """

    @property
    def name(self) -> str:
        return "cloud_enum"

    @property
    def description(self) -> str:
        return "Enumerate potential cloud storage buckets for a target"

    @property
    def category(self) -> str:
        return "cloud"

    async def run(self, target: str) -> ToolResult:
        """Probe for common cloud storage buckets"""
        import time

        start_time = time.time()

        # Normalize target into something bucket-like
        domain = target.replace('https://', '').replace('http://', '').split('/')[0]
        base_parts = domain.split('.')
        base_name = base_parts[0] if base_parts else domain

        candidates = {
            domain,
            domain.replace('.', '-'),
            domain.replace('.', ''),
            base_name,
            f"{base_name}-assets",
            f"{base_name}-static",
            f"{base_name}-files",
            f"{base_name}-media",
            f"{base_name}-cdn",
        }

        providers = [
            ("aws_s3", "https://{bucket}.s3.amazonaws.com"),
            ("gcp_storage", "https://storage.googleapis.com/{bucket}"),
            ("azure_blob", "https://{bucket}.blob.core.windows.net"),
        ]

        timeout = aiohttp.ClientTimeout(total=10)
        interesting_statuses = {200, 301, 302, 307, 308, 401, 403, 405}
        discovered: List[Dict[str, Any]] = []
        timeouts = 0

        async with aiohttp.ClientSession(headers={'User-Agent': 'recon-again/0.1.0'}) as session:
            nonlocal_timeouts = [0]

            async def probe(provider: str, template: str, bucket: str):
                url = template.format(bucket=bucket)
                try:
                    async with session.head(url, timeout=timeout, allow_redirects=True) as response:
                        status = response.status

                        # Some providers return helpful bodies for non-existent buckets
                        body = ""
                        if status not in interesting_statuses:
                            try:
                                body = await response.text()
                            except Exception:
                                body = ""

                        if status in interesting_statuses:
                            access = 'public' if status == 200 else 'restricted'
                            return {
                                'provider': provider,
                                'bucket': bucket,
                                'url': url,
                                'status': status,
                                'access': access
                            }

                        if 'NoSuchBucket' in body or 'The specified bucket does not exist' in body:
                            return None

                        return None
                except asyncio.TimeoutError:
                    nonlocal_timeouts[0] += 1
                    return None
                except Exception as e:  # pragma: no cover - network dependent
                    logger.debug(f"{provider} probe failed for {bucket}: {e}")
                    return None

            tasks = [
                probe(provider, template, bucket)
                for bucket in candidates
                for provider, template in providers
            ]

            results = await asyncio.gather(*tasks)

            for result in results:
                if result:
                    discovered.append(result)

            timeouts = nonlocal_timeouts[0]

        execution_time = time.time() - start_time

        metadata = {
            'providers_checked': [p[0] for p in providers],
            'candidate_buckets': len(candidates),
            'checks_performed': len(candidates) * len(providers),
            'timeouts': timeouts,
        }

        return self._create_result(
            target=target,
            success=True,
            data={
                'resources': discovered,
                'found_count': len(discovered),
            },
            execution_time=execution_time,
            metadata=metadata,
        )


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


class PhonebookTool(BaseTool):
    """
    phonebook.cz API for employee and contact enumeration
    Free API, no auth required
    """
    
    @property
    def name(self) -> str:
        return "phonebook"
    
    @property
    def description(self) -> str:
        return "Employee and contact enumeration using phonebook.cz API"
    
    @property
    def category(self) -> str:
        return "osint"
    
    async def run(self, target: str) -> ToolResult:
        """Query phonebook.cz for employees and contacts"""
        import time
        start_time = time.time()
        
        try:
            domain = target.replace('https://', '').replace('http://', '').split('/')[0]
            
            # phonebook.cz API endpoints
            # Email search: https://phonebook.cz/api/v1/search/emails?domain=example.com
            # Phone search: https://phonebook.cz/api/v1/search/phones?domain=example.com
            
            emails = []
            phones = []
            
            async with aiohttp.ClientSession() as session:
                # Search for emails
                email_url = f"https://phonebook.cz/api/v1/search/emails?domain={quote(domain)}"
                try:
                    async with session.get(
                        email_url,
                        headers={'User-Agent': 'recon-again/0.1.0'},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if isinstance(data, dict):
                                emails = data.get('emails', [])
                            elif isinstance(data, list):
                                emails = data
                except Exception as e:
                    logger.debug(f"Email search failed: {e}")
                
                # Search for phone numbers
                phone_url = f"https://phonebook.cz/api/v1/search/phones?domain={quote(domain)}"
                try:
                    async with session.get(
                        phone_url,
                        headers={'User-Agent': 'recon-again/0.1.0'},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if isinstance(data, dict):
                                phones = data.get('phones', [])
                            elif isinstance(data, list):
                                phones = data
                except Exception as e:
                    logger.debug(f"Phone search failed: {e}")
            
            execution_time = time.time() - start_time
            
            if emails or phones:
                return self._create_result(
                    target=target,
                    success=True,
                    data={
                        'emails': emails,
                        'phones': phones,
                        'email_count': len(emails),
                        'phone_count': len(phones),
                        'total_contacts': len(emails) + len(phones)
                    },
                    execution_time=execution_time,
                    metadata={'source': 'phonebook.cz'}
                )
            else:
                return self._create_result(
                    target=target,
                    success=False,
                    error="No contacts found",
                    execution_time=execution_time
                )
        except Exception as e:
            logger.error(f"phonebook.cz error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )

class EmployeeSocialTool(BaseTool):
    """
    Find potential employee social media profiles via DuckDuckGo

    This tool performs search engine queries against common social media platforms
    (LinkedIn, Twitter, GitHub, Facebook, Instagram) looking for profiles that
    reference the target's domain or identifier."""
    
class HunterTool(BaseTool):
    """
    Hunter.io domain search for employee contact discovery
    Requires Hunter.io API key
    """

    @property
    def name(self) -> str:
        return "hunter"

    @property
    def description(self) -> str:
        return "Discover emails and employees via Hunter.io domain search"

    @property
    def category(self) -> str:
        return "osint"

    @property
    def requires_auth(self) -> bool:
        return True

    async def run(self, target: str) -> ToolResult:
        """Query Hunter.io for employee emails on a domain"""
        import time

        start_time = time.time()
        api_key = self.config.get('hunter', {}).get('api_key')

        if not api_key:
            return self._create_result(
                target=target,
                success=False,
                error="Hunter.io API key not configured"
            )

        try:
            domain = target.replace('https://', '').replace('http://', '').split('/')[0]
            url = (
                "https://api.hunter.io/v2/domain-search?"
                f"domain={quote(domain)}&api_key={quote(api_key)}&limit=100"
            )

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={'User-Agent': 'recon-again/0.1.0'},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        execution_time = time.time() - start_time
                        return self._create_result(
                            target=target,
                            success=False,
                            error=f"HTTP {response.status}",
                            execution_time=execution_time
                        )

                    data = await response.json()
                    payload = data.get('data', {}) if isinstance(data, dict) else {}
                    emails = payload.get('emails', []) if isinstance(payload, dict) else []
                    meta = payload.get('meta', {}) if isinstance(payload, dict) else {}

                    simplified = []
                    for email in emails:
                        if isinstance(email, dict):
                            simplified.append({
                                'value': email.get('value'),
                                'first_name': email.get('first_name'),
                                'last_name': email.get('last_name'),
                                'position': email.get('position'),
                                'seniority': email.get('seniority'),
                                'department': email.get('department'),
                                'source_domain': domain
                            })

                    execution_time = time.time() - start_time
                    return self._create_result(
                        target=target,
                        success=True,
                        data={
                            'emails': simplified,
                            'email_count': len(simplified),
                            'sources': meta.get('results') if isinstance(meta, dict) else None
                        },
                        execution_time=execution_time,
                        metadata={'source': 'hunter.io'}
                    )
        except Exception as e:
            logger.error(f"Hunter.io error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )


class ClearbitProspectorTool(BaseTool):
    """
    Clearbit Prospector API for finding people at a company domain
    Requires Clearbit API key
    """

    @property
    def name(self) -> str:
        return "employee_social"

    @property
    def description(self) -> str:
        return "Find employees and contact roles using Clearbit Prospector"

    @property
    def category(self) -> str:
        return "osint"

    async def _search_duckduckgo(self, session: aiohttp.ClientSession, query: str, limit: int = 15) -> List[str]:
        """Perform a DuckDuckGo HTML search and extract result URLs"""
        url = f"https://duckduckgo.com/html/?q={quote(query)}"
        async with session.get(
            url,
            headers={'User-Agent': 'recon-again/0.1.0'},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status != 200:
                return []

            html = await response.text()
            links = re.findall(r'<a[^>]+class=\"result__a\"[^>]+href=\"(.*?)\"', html, flags=re.IGNORECASE)
            cleaned = []
            for link in links:
                link = link.replace('https://duckduckgo.com/l/?kh=-1&uddg=', '')
                cleaned.append(link)
            return cleaned[:limit]
          
    @property
    def requires_auth(self) -> bool:
        return True

    async def run(self, target: str) -> ToolResult:
        """Query Clearbit Prospector for people at the target domain"""
        import time

        start_time = time.time()
        api_key = self.config.get('clearbit', {}).get('api_key')

        if not api_key:
            return self._create_result(
                target=target,
                success=False,
                error="Clearbit API key not configured"
            )

        try:
            domain = target.replace('https://', '').replace('http://', '').split('/')[0]
            url = f"https://prospector.clearbit.com/v1/people/search?domain={quote(domain)}"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    auth=aiohttp.BasicAuth(api_key, ''),
                    headers={'User-Agent': 'recon-again/0.1.0'},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        execution_time = time.time() - start_time
                        return self._create_result(
                            target=target,
                            success=False,
                            error=f"HTTP {response.status}",
                            execution_time=execution_time
                        )

                    data = await response.json()
                    people = data.get('results', []) if isinstance(data, dict) else []
                    simplified = []
                    for person in people:
                        if not isinstance(person, dict):
                            continue
                        simplified.append({
                            'name': person.get('name'),
                            'title': person.get('title'),
                            'seniority': person.get('seniority'),
                            'department': person.get('department'),
                            'email': person.get('email'),
                            'linkedin': person.get('linkedin'),
                            'location': person.get('location')
                        })

                    execution_time = time.time() - start_time
                    return self._create_result(
                        target=target,
                        success=True,
                        data={
                            'people': simplified,
                            'people_count': len(simplified),
                            'pending': data.get('pending') if isinstance(data, dict) else None
                        },
                        execution_time=execution_time,
                        metadata={'source': 'clearbit-prospector'}
                    )
        except Exception as e:
            logger.error(f"Clearbit Prospector error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )


class PeopleDataLabsTool(BaseTool):
    """
    People Data Labs person search API
    Requires People Data Labs API key
    """

    @property
    def name(self) -> str:
        return "peopledatalabs"

    @property
    def description(self) -> str:
        return "Search People Data Labs for employees and contact metadata"

    @property
    def category(self) -> str:
        return "osint"

    @property
    def requires_auth(self) -> bool:
        return True

    async def run(self, target: str) -> ToolResult:
        """Query People Data Labs for people associated with a company domain"""
        import time

        start_time = time.time()
        api_key = self.config.get('peopledatalabs', {}).get('api_key')

        if not api_key:
            return self._create_result(
                target=target,
                success=False,
                error="People Data Labs API key not configured"
            )

        try:
            domain = target.replace('https://', '').replace('http://', '').split('/')[0]
            url = (
                "https://api.peopledatalabs.com/v5/person/search?"
                f"api_key={quote(api_key)}&company.domain={quote(domain)}&size=25"
            )

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={'User-Agent': 'recon-again/0.1.0'},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        execution_time = time.time() - start_time
                        return self._create_result(
                            target=target,
                            success=False,
                            error=f"HTTP {response.status}",
                            execution_time=execution_time
                        )

                    data = await response.json()
                    matches = data.get('data', []) if isinstance(data, dict) else []
                    simplified = []
                    for person in matches:
                        if not isinstance(person, dict):
                            continue
                        simplified.append({
                            'full_name': person.get('full_name'),
                            'title': person.get('job_title'),
                            'seniority': person.get('job_seniority'),
                            'department': person.get('job_department'),
                            'emails': person.get('emails'),
                            'profiles': person.get('profiles')
                        })

                    execution_time = time.time() - start_time
                    return self._create_result(
                        target=target,
                        success=True,
                        data={
                            'people': simplified,
                            'people_count': len(simplified),
                            'total_available': data.get('total') if isinstance(data, dict) else None
                        },
                        execution_time=execution_time,
                        metadata={'source': 'people-data-labs'}
                    )
        except Exception as e:
            logger.error(f"People Data Labs error: {e}")
            return self._create_result(
                target=target,
                success=False,
                error=str(e)
            )

