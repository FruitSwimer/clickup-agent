#!/usr/bin/env python3
"""
Test script to isolate MCP server hanging issue.
"""
import os
import asyncio
import logging
import sys
from dotenv import load_dotenv
from src.agent.mcp_servers import create_clickup_mcp_server

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_mcp_server():
    """Test MCP server creation and cleanup."""
    print("🔌 Creating MCP server...")
    server = create_clickup_mcp_server()
    print("✅ MCP server created")
    
    print("🔌 Starting MCP server...")
    try:
        print("🔌 Entering async context manager...")
        async with server:
            print("✅ MCP server started successfully!")
            print("🔍 Listing tools...")
            try:
                tools = await server.list_tools()
                print(f"✅ Found {len(tools)} tools")
            except Exception as e:
                print(f"⚠️  Error listing tools: {e}")
            
            print("⏱️  Sleeping for 2 seconds...")
            await asyncio.sleep(2.0)
            print("🔌 Closing MCP server...")
    except Exception as e:
        print(f"❌ Error during server operation: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    print("✅ MCP server closed")
    print("🧹 Cleaning up...")
    
    # Give time for cleanup
    await asyncio.sleep(0.5)
    
    print("✅ Test completed")

async def main_with_timeout():
    """Run test with timeout."""
    try:
        await asyncio.wait_for(test_mcp_server(), timeout=40.0)
    except asyncio.TimeoutError:
        print("❌ Test timed out after 40 seconds")
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main_with_timeout())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    
    print("✅ Exiting cleanly")
    os._exit(0)