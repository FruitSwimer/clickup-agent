"""
MCP Server configurations for Pydantic AI agents.
"""
import os
from pydantic_ai.mcp import MCPServerStdio
from dotenv import load_dotenv
load_dotenv()

MCPServerClickup = MCPServerStdio(  
    'npx',
    args=[
        '-y',
        '@taazkareem/clickup-mcp-server@latest'
    ],
    env={
        'CLICKUP_API_KEY': os.environ.get('CLICKUP_API_KEY'),
        'CLICKUP_TEAM_ID': os.environ.get('CLICKUP_TEAM_ID'),
    }
)