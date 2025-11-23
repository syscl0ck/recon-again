"""Web scraping tools for corporate sites."""

import asyncio
import logging
import re
from typing import Dict, List, Set
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class CorporateSiteScraperTool(BaseTool):
    """Scrape the main corporate site for contact and employee information."""

    @property
    def name(self) -> str:
        return "corporate_site"

    @property
    def description(self) -> str:
        return "Scrape corporate site pages for emails, phones, and employee listings"

    @property
    def category(self) -> str:
        return "web"

    async def _fetch_page(self, session: aiohttp.ClientSession, url: str) -> str:
        try:
            async with session.get(
                url,
                headers={"User-Agent": "recon-again/0.1.0"},
                timeout=aiohttp.ClientTimeout(total=min(self.timeout, 30)),
            ) as response:
                if response.status == 200:
                    return await response.text()
                logger.debug("Non-200 status %s for %s", response.status, url)
        except asyncio.TimeoutError:
            logger.debug("Timeout while fetching %s", url)
        except Exception as exc:  # pragma: no cover - network errors
            logger.debug("Request error for %s: %s", url, exc)
        return ""

    def _extract_emails(self, html: str) -> Set[str]:
        email_pattern = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
        return set(email_pattern.findall(html))

    def _extract_phone_numbers(self, html: str) -> Set[str]:
        phone_pattern = re.compile(r"\+?\d[\d\s().-]{7,}\d")
        numbers = {match.strip() for match in phone_pattern.findall(html)}
        return {number for number in numbers if len(number) >= 8}

    def _collect_social_links(self, soup: BeautifulSoup, social_links: Dict[str, Set[str]]):
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            lower_href = href.lower()
            if "linkedin.com" in lower_href:
                social_links["linkedin"].add(href)
            if "twitter.com" in lower_href or "x.com" in lower_href:
                social_links["twitter"].add(href)
            if "facebook.com" in lower_href:
                social_links["facebook"].add(href)
            if "instagram.com" in lower_href:
                social_links["instagram"].add(href)
            if "github.com" in lower_href:
                social_links["github"].add(href)

    def _infer_title_from_context(self, element, matched_text: str) -> str:
        trailing = element.get_text(" ", strip=True)
        trailing = trailing.split(matched_text, 1)[-1].strip(" -,:|")
        if trailing and 1 <= len(trailing.split()) <= 8:
            return trailing

        for sibling in element.next_siblings:
            if isinstance(sibling, str):
                candidate = sibling.strip()
            else:
                candidate = sibling.get_text(" ", strip=True) if hasattr(sibling, "get_text") else ""
            if candidate and 1 <= len(candidate.split()) <= 8:
                return candidate

        parent = element.find_parent()
        if parent:
            for child in parent.find_all(["p", "span", "div"], recursive=False):
                candidate = child.get_text(" ", strip=True)
                if candidate and 1 <= len(candidate.split()) <= 8 and candidate != matched_text:
                    return candidate
        return ""

    def _extract_employees(self, soup: BeautifulSoup, page: str, seen: Set[str]) -> List[Dict[str, str]]:
        employee_entries: List[Dict[str, str]] = []
        name_pattern = re.compile(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b")
        keywords = {"team", "people", "member", "staff", "employee", "leadership", "person", "bio"}

        candidate_elements = []
        for element in soup.find_all(True):
            if any(keyword in (" ".join(element.get("class", [])).lower()) for keyword in keywords):
                candidate_elements.append(element)
                continue
            element_id = element.get("id", "").lower()
            if any(keyword in element_id for keyword in keywords):
                candidate_elements.append(element)

        for element in candidate_elements:
            text = " ".join(element.stripped_strings)
            if len(text) < 5:
                continue

            for match in name_pattern.finditer(text):
                name = match.group(1).strip()
                lowered = name.lower()
                if lowered in seen:
                    continue

                title = self._infer_title_from_context(element, match.group(0))
                employee_entries.append({"name": name, "title": title or None, "page": page})
                seen.add(lowered)

        return employee_entries

    async def run(self, target: str) -> ToolResult:
        import time

        start_time = time.time()
        domain = target.replace("https://", "").replace("http://", "").split("/")[0]
        base_url = target if target.startswith("http") else f"https://{domain}"

        candidate_paths = [
            "/",
            "/about",
            "/company",
            "/team",
            "/people",
            "/leadership",
            "/staff",
        ]

        social_links: Dict[str, Set[str]] = {
            "linkedin": set(),
            "twitter": set(),
            "facebook": set(),
            "instagram": set(),
            "github": set(),
        }
        emails: Set[str] = set()
        phones: Set[str] = set()
        employees: List[Dict[str, str]] = []
        seen_names: Set[str] = set()
        pages_scraped: List[Dict[str, str]] = []
        page_titles: Dict[str, str] = {}

        async with aiohttp.ClientSession() as session:
            for path in candidate_paths:
                url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/")) if path != "/" else base_url
                html = await self._fetch_page(session, url)
                if not html:
                    continue

                soup = BeautifulSoup(html, "html.parser")
                title_text = soup.title.string.strip() if soup.title and soup.title.string else ""
                if title_text:
                    page_titles[path] = title_text

                pages_scraped.append({"path": path, "url": url, "length": len(html)})
                emails.update(self._extract_emails(html))
                phones.update(self._extract_phone_numbers(html))
                self._collect_social_links(soup, social_links)
                employees.extend(self._extract_employees(soup, path, seen_names))

        execution_time = time.time() - start_time

        if not pages_scraped:
            return self._create_result(
                target=target,
                success=False,
                error="Unable to retrieve corporate site pages",
                execution_time=execution_time,
            )

        has_social = any(bool(values) for values in social_links.values())
        success = bool(emails or phones or has_social or employees or page_titles)

        data = {
            "pages_scraped": pages_scraped,
            "page_titles": page_titles,
            "emails": sorted(emails),
            "phone_numbers": sorted(phones),
            "social_links": {key: sorted(values) for key, values in social_links.items() if values},
            "employee_listings": employees,
        }

        return self._create_result(
            target=target,
            success=success,
            data=data,
            execution_time=execution_time,
            metadata={
                "source": "corporate_site_scraper",
                "pages_attempted": len(candidate_paths),
                "pages_retrieved": len(pages_scraped),
                "employees_found": len(employees),
            },
        )

