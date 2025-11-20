# New Passive Tools Added

## Overview

Added 5 new passive reconnaissance tools that don't require API keys and don't directly scan infrastructure. All tools are free and open-source.

## New Tools

### 1. theHarvester
- **Category**: OSINT
- **Type**: Passive email and subdomain harvesting
- **Installation**: `pip install theHarvester`
- **Description**: Collects emails, subdomains, hosts, and IPs from various public sources
- **Sources**: Google, Bing, LinkedIn, Twitter, GitHub, and more
- **Use Case**: Initial reconnaissance to gather email addresses and subdomains

### 2. gau (Get All URLs)
- **Category**: Web
- **Type**: URL extraction from archives
- **Installation**: Go binary from GitHub releases
- **Description**: Fetches known URLs from AlienVault's Open Threat Exchange, Wayback Machine, Common Crawl, and URLScan
- **Use Case**: Discover historical URLs and endpoints

### 3. Holehe
- **Category**: OSINT
- **Type**: Email account existence checker
- **Installation**: `pip install holehe`
- **Description**: Checks if an email address is registered on various platforms
- **Platforms**: 120+ websites including social media, forums, and services
- **Use Case**: Verify email account existence across platforms

### 4. Maigret
- **Category**: OSINT
- **Type**: Username enumeration
- **Installation**: `pip install maigret`
- **Description**: More aggressive username search across platforms than Sherlock
- **Platforms**: 500+ websites
- **Use Case**: Find all accounts associated with a username

### 5. Arjun
- **Category**: Web
- **Type**: HTTP parameter discovery
- **Installation**: `pip install arjun`
- **Description**: Discovers HTTP parameters in web applications
- **Mode**: Passive (can also do active scanning)
- **Use Case**: Find hidden parameters in web applications

## Tool Count

**Total Tools**: 12
- **API-based**: 3 (crt_sh, urlscan, hibp)
- **Python-based**: 9 (sublist3r, dnsrecon, wayback, sherlock, theharvester, gau, holehe, maigret, arjun)

## Usage Examples

### theHarvester
```bash
recon-again example.com -t theharvester
```

### gau
```bash
recon-again example.com -t gau
```

### Holehe
```bash
recon-again user@example.com -t holehe
```

### Maigret
```bash
recon-again username -t maigret
```

### Arjun
```bash
recon-again https://example.com -t arjun
```

## Docker Installation

All tools are automatically installed in the Docker image:
- Python tools installed via pip
- gau installed as Go binary (if available)
- All tools registered and ready to use

## Notes

- All tools are **passive** - they don't directly scan target infrastructure
- No API keys required for any of these tools
- All tools are **free** and open-source
- Results are stored in SQLite database
- JSON backups are created for compatibility

## Future Additions

Potential passive tools to add:
- tko-subs (subdomain takeover detection)
- github-subdomains (GitHub subdomain discovery)
- git-dorker (GitHub dorking)
- Infoga (email OSINT)

---

**Status**: ✅ All 5 tools implemented and tested





