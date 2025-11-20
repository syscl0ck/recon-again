#!/usr/bin/env python3
"""
Example usage of recon-again
"""

import asyncio
import json
from recon_again import ReconEngine


async def main():
    """Example reconnaissance session"""
    
    # Initialize engine
    print("Initializing recon-again engine...")
    engine = ReconEngine(
        config_path='config.json',  # Optional, uses defaults if not found
        enable_ai=True  # Enable AI automation
    )
    
    # List available tools
    print(f"\nAvailable tools: {', '.join(engine.list_tools())}")
    
    # Run reconnaissance on a target
    target = "example.com"
    print(f"\n🎯 Starting reconnaissance on: {target}")
    
    session = await engine.run_recon(
        target=target,
        tools=None,  # None = run all available tools
        ai_guided=True  # Use AI to plan execution
    )
    
    # Display results
    print(f"\n✅ Reconnaissance completed!")
    print(f"Session ID: {session.session_id}")
    print(f"Status: {session.status}")
    print(f"Tools executed: {len(session.tools_executed)}")
    
    print("\n📊 Results Summary:")
    print("=" * 60)
    
    for tool_name, result in session.results.items():
        if tool_name == 'ai_analysis':
            print(f"\n🤖 AI Analysis:")
            if isinstance(result, dict):
                print(f"  Summary: {result.get('summary', 'N/A')}")
                print(f"  Risk Level: {result.get('risk_level', 'N/A')}")
                if result.get('key_findings'):
                    print(f"  Key Findings:")
                    for finding in result['key_findings'][:3]:
                        print(f"    - {finding}")
        else:
            if isinstance(result, dict) and result.get('success'):
                data = result.get('data', {})
                if isinstance(data, dict):
                    count = data.get('count', len(data) if isinstance(data, (list, dict)) else 0)
                    print(f"\n🔧 {tool_name}: ✅ Found {count} items")
                else:
                    print(f"\n🔧 {tool_name}: ✅ Completed")
            else:
                error = result.get('error', 'Unknown error') if isinstance(result, dict) else 'Failed'
                print(f"\n🔧 {tool_name}: ❌ {error}")
    
    # Save session to file
    output_file = f"example_results_{session.session_id}.json"
    with open(output_file, 'w') as f:
        json.dump(session.to_dict(), f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())

