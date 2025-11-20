"""
Command-line interface for recon-again
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path

from .core.engine import ReconEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print recon-again banner"""
    banner = """
    ╔═══════════════════════════════════════════════════╗
    ║         recon-again v0.1.0                        ║
    ║    AI-Powered Reconnaissance Framework            ║
    ╚═══════════════════════════════════════════════════╝
    """
    print(banner)


def print_results(session):
    """Pretty print session results"""
    print(f"\n{'='*60}")
    print(f"Recon Results for: {session.target}")
    print(f"Session ID: {session.session_id}")
    print(f"Status: {session.status}")
    print(f"{'='*60}\n")
    
    for tool_name, result in session.results.items():
        if tool_name == 'ai_analysis':
            print(f"\n🤖 AI Analysis:")
            print(f"{'-'*60}")
            if isinstance(result, dict):
                for key, value in result.items():
                    if isinstance(value, list):
                        print(f"  {key}:")
                        for item in value[:5]:  # Show first 5
                            print(f"    - {item}")
                    else:
                        print(f"  {key}: {value}")
            print()
        else:
            print(f"\n🔧 {tool_name.upper()}:")
            print(f"{'-'*60}")
            if isinstance(result, dict):
                if result.get('success'):
                    data = result.get('data', {})
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, list):
                                count = len(value)
                                print(f"  {key}: {count} items")
                                # Show first few items
                                for item in value[:3]:
                                    print(f"    - {item}")
                                if count > 3:
                                    print(f"    ... and {count - 3} more")
                            else:
                                print(f"  {key}: {value}")
                    else:
                        print(f"  Result: {data}")
                    print(f"  Execution time: {result.get('execution_time', 0):.2f}s")
                else:
                    print(f"  ❌ Error: {result.get('error', 'Unknown error')}")
            print()


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='recon-again: AI-powered reconnaissance framework',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'target',
        help='Target domain, IP, or identifier'
    )
    
    parser.add_argument(
        '-c', '--config',
        help='Path to configuration file',
        default=None
    )
    
    parser.add_argument(
        '-t', '--tools',
        nargs='+',
        help='Specific tools to run (default: all)',
        default=None
    )
    
    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Disable AI automation'
    )
    
    parser.add_argument(
        '-l', '--list-tools',
        action='store_true',
        help='List all available tools and exit'
    )
    
    parser.add_argument(
        '--tool-info',
        help='Show information about a specific tool'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file for JSON results',
        default=None
    )
    
    parser.add_argument(
        '--db-path',
        help='Path to SQLite database (overrides config)',
        default=None
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print_banner()
    
    # Initialize engine
    try:
        engine = ReconEngine(
            config_path=args.config,
            enable_ai=not args.no_ai,
            db_path=args.db_path
        )
    except Exception as e:
        logger.error(f"Failed to initialize engine: {e}")
        sys.exit(1)
    
    # List tools
    if args.list_tools:
        print("\nAvailable Tools:")
        print("-" * 60)
        for tool_name in engine.list_tools():
            info = engine.get_tool_info(tool_name)
            if info:
                print(f"  {tool_name}")
                print(f"    Description: {info['description']}")
                print(f"    Category: {info['category']}")
                print(f"    Requires Auth: {info['requires_auth']}")
                print()
        sys.exit(0)
    
    # Tool info
    if args.tool_info:
        info = engine.get_tool_info(args.tool_info)
        if info:
            print(f"\nTool: {args.tool_info}")
            print("-" * 60)
            for key, value in info.items():
                print(f"  {key}: {value}")
        else:
            print(f"Tool '{args.tool_info}' not found")
        sys.exit(0)
    
    # Run reconnaissance
    if not args.target:
        parser.print_help()
        sys.exit(1)
    
    print(f"\n🎯 Starting reconnaissance on: {args.target}")
    print(f"🤖 AI Automation: {'Enabled' if not args.no_ai else 'Disabled'}")
    if args.tools:
        print(f"🔧 Tools: {', '.join(args.tools)}")
    print()
    
    try:
        session = await engine.run_recon(
            target=args.target,
            tools=args.tools,
            ai_guided=not args.no_ai
        )
        
        # Print results
        print_results(session)
        
        # Save to file if requested
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                json.dump(session.to_dict(), f, indent=2)
            print(f"\n✅ Results saved to: {output_path}")
        
        print(f"\n✅ Reconnaissance completed!")
        print(f"📁 Session saved to: {engine.results_dir}/{session.session_id}.json")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Reconnaissance failed: {e}")
        sys.exit(1)


def cli_entry():
    """Entry point for CLI"""
    asyncio.run(main())


if __name__ == '__main__':
    cli_entry()

