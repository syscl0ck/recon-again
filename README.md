# recon-again

**AI-Powered Reconnaissance Framework**

recon-again is a modern, modular reconnaissance framework that combines the power of multiple open-source tools with AI-driven automation via OpenRouter. Built for security researchers, bug bounty hunters, and penetration testers who want intelligent, automated reconnaissance workflows.

## 🚀 Features

- **Modular Architecture**: Easy to extend with new tools
- **AI Automation**: OpenRouter integration for intelligent tool selection and result analysis
- **Free Tools First**: Implements the easiest and free tools from the comprehensive TOOLS.md list
- **VSCode Extension**: Full IDE integration for seamless reconnaissance workflows
- **Async Execution**: Concurrent tool execution for maximum efficiency
- **Result Aggregation**: Unified results format across all tools
- **Graph Insights**: Optional Neo4j backend for relationship-driven contact intelligence

## 📋 Implemented Tools

### API-Based (No Installation Required)
- **crt.sh** - Certificate transparency log search
- **urlscan.io** - Historical scan search and domain discovery
- **Have I Been Pwned** - Breach database lookup
- **CloudEnum** - Cloud storage bucket discovery across AWS, GCP, and Azure
- **phonebook.cz** - Employee and contact enumeration (emails & phone numbers)

### Python-Based (Require Dependencies)
- **Sublist3r** - Subdomain enumeration
- **DNSRecon** - DNS record enumeration
- **Wayback Machine** - Historical URL extraction
- **Sherlock** - Username enumeration across platforms
- **Corporate site scraper** - Scrape main pages for contact details and employee listings
- **theHarvester** - Passive email and subdomain harvesting
- **gau** - URL extraction from common sources
- **Holehe** - Email account existence checker
- **Maigret** - Username enumeration (more aggressive than Sherlock)
- **Arjun** - HTTP parameter discovery
- **EmailHarvester** - Email address discovery from search engines

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- pip
- SQLite3 (usually pre-installed)
- (Optional) [Neo4j](https://neo4j.com/) when storing contacts as a graph

### Basic Installation

```bash
# Clone the repository
git clone https://github.com/recon-again/recon-again.git
cd recon-again

# Install core dependencies
pip install -r requirements.txt

# Install the package
pip install -e .

# Initialize database
recon-again-init-db
```

### Docker Installation (Recommended)

```bash
# Build Docker image
docker build -t recon-again:latest .

# Or use docker-compose
docker-compose up -d

# Initialize database in container
docker-compose exec recon-again recon-again-init-db
```

See [DOCKER.md](DOCKER.md) for detailed Docker documentation.

### Optional Tool Dependencies

For full functionality, install optional dependencies:

```bash
# Install Python-based tools
pip install sublist3r dnsrecon waybackpy

# Or install external tools separately:
# - sherlock: https://github.com/sherlock-project/sherlock
# - gau: https://github.com/lc/gau
# - theHarvester: https://github.com/laramies/theHarvester
# - holehe: https://github.com/megadose/holehe
# - maigret: https://github.com/soxoj/maigret
# - arjun: https://github.com/s0md3v/Arjun
# - waybackurls: https://github.com/tomnomnom/waybackurls
```

## ⚙️ Configuration

1. Copy the example configuration:
```bash
cp config.example.json config.json
```

2. Edit `config.json`:
```json
{
  "results_dir": "./results",
  "db_path": "./data/recon_again.db",
  "openrouter": {
    "api_key": "your-openrouter-api-key-here",
    "model": "openai/gpt-4-turbo",
    "base_url": "https://openrouter.ai/api/v1"
  },
  "hibp": {
    "api_key": "your-hibp-api-key-here-optional"
  },
  "graph": {
    "enabled": true,
    "uri": "bolt://neo4j:7687",
    "user": "neo4j",
    "password": "change-me",
    "database": "neo4j"
  },
  "tools": {
    "timeout": 300,
    "max_concurrent": 5
  }
}
```

3. Get your OpenRouter API key from [OpenRouter.ai](https://openrouter.ai)

4. Initialize the database:
```bash
recon-again-init-db
```

## 🎯 Usage

### Command Line

#### Basic Usage
```bash
# Run full reconnaissance with AI automation
recon-again example.com

# Run specific tools
recon-again example.com -t crt_sh urlscan hibp

# Disable AI automation
recon-again example.com --no-ai

# Use custom config
recon-again example.com -c /path/to/config.json
```

#### List Available Tools
```bash
recon-again --list-tools
```

#### Get Tool Information
```bash
recon-again --tool-info crt_sh
```

#### Save Results to File
```bash
recon-again example.com -o results.json
```

### Python API

```python
import asyncio
from recon_again import ReconEngine

async def main():
    # Initialize engine
    engine = ReconEngine(config_path='config.json', enable_ai=True)
    
    # Run reconnaissance
    session = await engine.run_recon(
        target='example.com',
        tools=None,  # None = all tools
        ai_guided=True
    )
    
    # Access results
    print(f"Session ID: {session.session_id}")
    print(f"Tools executed: {session.tools_executed}")
    
    for tool_name, result in session.results.items():
        if result.get('success'):
            print(f"{tool_name}: {result.get('data')}")

asyncio.run(main())
```

## 🔌 VSCode Extension

### Installation

1. Open VSCode
2. Go to Extensions (Ctrl+Shift+X / Cmd+Shift+X)
3. Search for "recon-again"
4. Click Install

Or install from command line:
```bash
cd vscode-extension
npm install
npm run compile
code --install-extension recon-again-0.1.0.vsix
```

### Usage

1. **Run Reconnaissance**: 
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type "recon-again: Run Reconnaissance"
   - Enter your target

2. **View Results**:
   - Results appear in the "Recon Results" tree view
   - Click any result file to view details

3. **List Tools**:
   - Command: "recon-again: List Available Tools"

4. **Run Specific Tool**:
   - Command: "recon-again: Run Specific Tool"

### Extension Settings

- `recon-again.configPath`: Path to configuration file
- `recon-again.openrouterApiKey`: OpenRouter API key
- `recon-again.enableAI`: Enable/disable AI automation

## 🧠 AI Automation

recon-again uses OpenRouter to provide intelligent automation:

1. **Execution Planning**: AI analyzes the target and creates an optimal tool execution sequence
2. **Result Analysis**: AI analyzes all results and provides:
   - Summary of findings
   - Key discoveries
   - Recommendations for next steps
   - Risk assessment
   - Interesting targets to investigate

### Example AI Analysis Output

```json
{
  "summary": "Found 45 subdomains and 3 potential vulnerabilities",
  "key_findings": [
    "Multiple subdomains exposed",
    "Historical URLs reveal sensitive endpoints",
    "Certificate transparency shows staging environment"
  ],
  "recommendations": [
    "Run port scan on discovered IPs",
    "Check for subdomain takeovers",
    "Enumerate API endpoints"
  ],
  "risk_level": "medium",
  "interesting_targets": [
    "staging.example.com",
    "api.example.com"
  ]
}
```

## 💾 Database

recon-again uses **SQLite** for persistent storage of all reconnaissance data:

- **Sessions**: All reconnaissance sessions
- **Tool Results**: Results from every tool execution
- **Targets**: Target information and history
- **AI Analysis**: AI-generated insights and recommendations

### Database Features

- Automatic initialization on first run
- Queryable with SQL
- Backup and restore support
- Efficient indexing for fast queries

See [DATABASE.md](DATABASE.md) for complete database documentation.

### Quick Database Commands

```bash
# Initialize database
recon-again-init-db

# View database
sqlite3 ./data/recon_again.db

# Query sessions
sqlite3 ./data/recon_again.db "SELECT * FROM sessions ORDER BY start_time DESC LIMIT 10;"
```

## 📁 Project Structure

```
recon-again/
├── recon_again/
│   ├── __init__.py
│   ├── cli.py                 # Command-line interface
│   ├── core/
│   │   ├── engine.py          # Main orchestration engine
│   │   └── ai_pilot.py         # OpenRouter AI integration
│   ├── database/              # Database module
│   │   ├── connection.py      # Database connection
│   │   ├── models.py          # Database models
│   │   └── init_db.py         # Initialization script
│   └── tools/
│       ├── base.py             # Base tool classes
│       ├── api_tools.py         # API-based tools
│       └── python_tools.py     # Python-based tools
├── vscode-extension/           # VSCode extension
├── data/                       # Database files (created on init)
├── results/                    # JSON backup files
├── Dockerfile                  # Docker image definition
├── docker-compose.yml          # Docker Compose config
├── config.example.json         # Configuration template
├── requirements.txt            # Python dependencies
├── setup.py                    # Package setup
├── DOCKER.md                   # Docker documentation
├── DATABASE.md                 # Database documentation
└── README.md
```

## 🔧 Adding New Tools

To add a new tool, create a class inheriting from `BaseTool`:

```python
from .base import BaseTool, ToolResult

class MyNewTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "Description of my tool"
    
    @property
    def category(self) -> str:
        return "dns"  # or "web", "osint", etc.
    
    async def run(self, target: str) -> ToolResult:
        # Your tool logic here
        data = await do_something(target)
        
        return self._create_result(
            target=target,
            success=True,
            data=data
        )
```

Then register it in `recon_again/tools/__init__.py` and `core/engine.py`.

## 📊 Results Format

All tools return results in a standardized format:

```json
{
  "tool_name": "crt_sh",
  "target": "example.com",
  "success": true,
  "data": {
    "subdomains": ["www.example.com", "api.example.com"],
    "count": 2
  },
  "execution_time": 1.23,
  "metadata": {
    "source": "crt.sh"
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

## 🐛 Troubleshooting

### Tool Not Found
If a tool fails with "not found" error:
- Check if the tool is installed
- Verify it's in your PATH
- Install missing dependencies

### OpenRouter API Errors
- Verify your API key is correct
- Check your API quota/limits
- Ensure you have internet connectivity

### Import Errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Verify Python version: `python --version` (should be 3.8+)

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Additional tool integrations
- Better error handling
- More AI models support
- Enhanced VSCode extension features
- Performance optimizations

## 📝 License

See LICENSE file for details.

## 🙏 Acknowledgments

- All the amazing open-source tools listed in TOOLS.md
- OpenRouter for AI API access
- The security research community

## 🔮 Roadmap

- [ ] More tool integrations (from TOOLS.md)
- [ ] Result visualization dashboard
- [ ] Export to various formats (JSON, CSV, HTML)
- [ ] Integration with other security tools
- [ ] Multi-target batch processing
- [ ] Custom tool execution workflows
- [ ] Result correlation and intelligence

---

**Built with ❤️ for the security community**
