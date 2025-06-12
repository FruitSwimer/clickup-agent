"""
MCP Server connection utilities with retry logic.
"""
import asyncio
import logging
from typing import Optional
from pydantic_ai.mcp import MCPServerHTTP

logger = logging.getLogger(__name__)


async def connect_to_mcp_server(
    server: MCPServerHTTP, 
    max_retries: int = 5, 
    retry_delay: float = 2.0
) -> bool:
    """
    Connect to MCP server with retry logic.
    
    Args:
        server: The MCP server instance
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to MCP server (attempt {attempt + 1}/{max_retries})")
            # Test the connection by making a simple request
            async with server:
                logger.info("Successfully connected to MCP server")
                return True
        except Exception as e:
            logger.warning(f"Failed to connect to MCP server: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Max retries reached. Could not connect to MCP server.")
    
    return False


async def wait_for_mcp_server(url: str, timeout: float = 30.0) -> bool:
    """
    Wait for MCP server to be available.
    
    Args:
        url: The MCP server URL (can be health URL or SSE URL)
        timeout: Maximum time to wait in seconds
        
    Returns:
        bool: True if server becomes available, False if timeout
    """
    import aiohttp
    
    # If URL is already a health endpoint, use it directly
    if url.endswith('/health'):
        health_url = url
    else:
        # Extract base URL for health check
        base_url = url.replace('/sse', '')
        health_url = f"{base_url}/health"
    
    start_time = asyncio.get_event_loop().time()
    
    # Create session with timeout to avoid hanging connections
    timeout_config = aiohttp.ClientTimeout(total=2, connect=1)
    connector = aiohttp.TCPConnector(force_close=True)
    
    async with aiohttp.ClientSession(timeout=timeout_config, connector=connector) as session:
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                async with session.get(health_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"MCP server is healthy at {health_url}: {data}")
                        return True
            except asyncio.TimeoutError:
                logger.debug("Health check timed out")
            except Exception as e:
                logger.debug(f"Health check failed: {e}")
            
            await asyncio.sleep(1)
    
    logger.error(f"MCP server at {url} did not become available within {timeout} seconds")
    return False