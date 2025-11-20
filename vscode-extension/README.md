# recon-again VSCode Extension

VSCode extension for the recon-again reconnaissance framework.

## Features

- Run reconnaissance directly from VSCode
- View results from the database in a tree view
- Browse sessions, targets, and tool results
- List available tools
- Run specific tools
- AI-powered automation integration
- Displays data from `/data/recon_again.db` database

## Installation

### Command Line Installation

The easiest way to install the extension is using the provided installation script:

```bash
cd vscode-extension
./install.sh
```

This script will:
1. Install all dependencies
2. Compile the TypeScript code
3. Package the extension as a VSIX file
4. Install it in VSCode (if `code` command is available)

### Manual Installation

If you prefer to install manually:

```bash
cd vscode-extension
npm install
npm run compile
npm install -g @vscode/vsce
vsce package
code --install-extension recon-again-0.1.0.vsix
```

## Usage

1. Install the extension (see above)
2. Configure your OpenRouter API key in settings (optional)
3. Use the command palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) and search for "recon-again"
4. Select "Run Reconnaissance" and enter your target
5. View results in the "Recon Results" tree view in the Explorer sidebar

## Commands

- `recon-again.runRecon` - Run full reconnaissance on a target
- `recon-again.listTools` - List all available tools
- `recon-again.runTool` - Run a specific tool
- `recon-again.viewResults` - View saved results

## Configuration

- `recon-again.configPath` - Path to configuration file
- `recon-again.openrouterApiKey` - OpenRouter API key
- `recon-again.enableAI` - Enable/disable AI automation

