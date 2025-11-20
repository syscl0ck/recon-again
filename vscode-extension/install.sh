#!/bin/bash
# Installation script for recon-again VSCode extension

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔧 Installing recon-again VSCode extension..."

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm is not installed. Please install Node.js and npm first."
    exit 1
fi

# Check if code command is available
if ! command -v code &> /dev/null; then
    echo "⚠️  Warning: 'code' command not found. Make sure VSCode is installed and in your PATH."
    echo "   You can install the extension manually by:"
    echo "   1. Open VSCode"
    echo "   2. Press Ctrl+Shift+P (Cmd+Shift+P on Mac)"
    echo "   3. Type 'Extensions: Install from VSIX...'"
    echo "   4. Select the .vsix file from this directory"
    echo ""
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Compile TypeScript
echo "🔨 Compiling TypeScript..."
npm run compile

# Package extension
echo "📦 Packaging extension..."
npm run vscode:prepublish

# Check if vsce is installed
if ! command -v vsce &> /dev/null; then
    echo "📦 Installing vsce (VSCode Extension Manager)..."
    npm install -g @vscode/vsce
fi

# Create VSIX package
echo "📦 Creating VSIX package..."
vsce package --out recon-again-0.1.0.vsix

# Install extension if code command is available
if command -v code &> /dev/null; then
    echo "📥 Installing extension..."
    code --install-extension recon-again-0.1.0.vsix --force
    
    echo ""
    echo "✅ Extension installed successfully!"
    echo ""
    echo "To use the extension:"
    echo "  1. Open VSCode"
    echo "  2. Press Ctrl+Shift+P (Cmd+Shift+P on Mac)"
    echo "  3. Type 'recon-again' to see available commands"
    echo ""
else
    echo ""
    echo "✅ Extension packaged successfully!"
    echo ""
    echo "To install manually:"
    echo "  1. Open VSCode"
    echo "  2. Press Ctrl+Shift+P (Cmd+Shift+P on Mac)"
    echo "  3. Type 'Extensions: Install from VSIX...'"
    echo "  4. Select: $SCRIPT_DIR/recon-again-0.1.0.vsix"
    echo ""
fi




