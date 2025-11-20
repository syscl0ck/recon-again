# Quick Start Guide

Get up and running with recon-again in 5 minutes!

## 1. Installation

```bash
# Clone and install
git clone https://github.com/recon-again/recon-again.git
cd recon-again
pip install -r requirements.txt
pip install -e .
```

## 2. Configuration (Optional)

```bash
# Copy example config
cp config.example.json config.json

# Edit config.json and add your OpenRouter API key
# Get one at: https://openrouter.ai
```

## 3. Run Your First Recon

### Command Line
```bash
# Basic usage
recon-again example.com

# With specific tools
recon-again example.com -t crt_sh urlscan

# Save results
recon-again example.com -o my_results.json
```

### Python Script
```python
import asyncio
from recon_again import ReconEngine

async def main():
    engine = ReconEngine(enable_ai=True)
    session = await engine.run_recon("example.com")
    print(f"Found {len(session.tools_executed)} tools executed")

asyncio.run(main())
```

## 4. View Results

Results are automatically saved to `./results/` directory in JSON format.

```bash
# View latest results
ls -lt results/ | head -5

# Pretty print results
cat results/example.com_*.json | python -m json.tool
```

## 5. VSCode Extension (Optional)

```bash
cd vscode-extension
npm install
npm run compile
```

Then in VSCode:
- Press `Ctrl+Shift+P`
- Type "recon-again: Run Reconnaissance"
- Enter your target

## Troubleshooting

**"Tool not found" errors**: Some tools require external installation. Check the tool's documentation in TOOLS.md.

**OpenRouter errors**: Make sure your API key is set in config.json. You can run without AI using `--no-ai` flag.

**Import errors**: Ensure you've run `pip install -e .` to install the package.

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [TOOLS.md](TOOLS.md) for the complete list of available tools
- Customize `config.json` for your needs
- Add your own tools by extending `BaseTool`

Happy reconning! 🚀

