"""
MCP Server configurations for Pydantic AI agents.
"""
import os
import sys
import logging
import signal
import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.message import SessionMessage
from pydantic_ai.mcp import MCPServerStdio
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class FixedMCPServerStdio(MCPServerStdio):
    """
    Custom MCP Server with proper Linux process termination.
    
    Fixes the issue where Linux processes don't properly terminate,
    causing the main process to hang on exit.
    """
    
    @asynccontextmanager
    async def client_streams(
        self,
    ) -> AsyncIterator[
        tuple[
            MemoryObjectReceiveStream[SessionMessage | Exception],
            MemoryObjectSendStream[SessionMessage],
        ]
    ]:
        """Fixed client streams with proper Linux process termination."""
        server = StdioServerParameters(command=self.command, args=list(self.args), env=self.env, cwd=self.cwd)
        
        # Use a patched stdio_client that properly handles Linux process termination
        async with self._patched_stdio_client(server) as (read_stream, write_stream):
            yield read_stream, write_stream
    
    @asynccontextmanager
    async def _patched_stdio_client(self, server: StdioServerParameters):
        """Patched stdio client with proper process termination for Linux."""
        from mcp.client.stdio import (
            get_default_environment, 
            _get_executable_command, 
            _create_platform_compatible_process
        )
        import anyio
        from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
        from anyio.streams.text import TextReceiveStream
        import mcp.types as types
        from mcp.shared.message import SessionMessage
        
        read_stream: MemoryObjectReceiveStream[SessionMessage | Exception]
        read_stream_writer: MemoryObjectSendStream[SessionMessage | Exception]
        write_stream: MemoryObjectSendStream[SessionMessage]
        write_stream_reader: MemoryObjectReceiveStream[SessionMessage]

        read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
        write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

        try:
            command = _get_executable_command(server.command)
            process = await _create_platform_compatible_process(
                command=command,
                args=server.args,
                env=({**get_default_environment(), **server.env} if server.env is not None else get_default_environment()),
                errlog=sys.stderr,
                cwd=server.cwd,
            )
        except OSError:
            # Clean up streams if process creation fails
            await read_stream.aclose()
            await write_stream.aclose()
            await read_stream_writer.aclose()
            await write_stream_reader.aclose()
            raise

        async def stdout_reader():
            assert process.stdout, "Opened process is missing stdout"
            try:
                async with read_stream_writer:
                    buffer = ""
                    async for chunk in TextReceiveStream(
                        process.stdout,
                        encoding=server.encoding,
                        errors=server.encoding_error_handler,
                    ):
                        lines = (buffer + chunk).split("\n")
                        buffer = lines.pop()
                        for line in lines:
                            try:
                                message = types.JSONRPCMessage.model_validate_json(line)
                            except Exception as exc:
                                await read_stream_writer.send(exc)
                                continue
                            session_message = SessionMessage(message)
                            await read_stream_writer.send(session_message)
            except anyio.ClosedResourceError:
                await anyio.lowlevel.checkpoint()

        async def stdin_writer():
            assert process.stdin, "Opened process is missing stdin"
            try:
                async with write_stream_reader:
                    async for session_message in write_stream_reader:
                        json = session_message.message.model_dump_json(by_alias=True, exclude_none=True)
                        await process.stdin.send(
                            (json + "\n").encode(
                                encoding=server.encoding,
                                errors=server.encoding_error_handler,
                            )
                        )
            except anyio.ClosedResourceError:
                await anyio.lowlevel.checkpoint()

        async with (
            anyio.create_task_group() as tg,
            process,
        ):
            tg.start_soon(stdout_reader)
            tg.start_soon(stdin_writer)
            try:
                yield read_stream, write_stream
            finally:
                # Improved process cleanup for Linux
                try:
                    if sys.platform == "win32":
                        # Windows cleanup (use existing logic)
                        from mcp.client.stdio.win32 import terminate_windows_process
                        await terminate_windows_process(process)
                    else:
                        # Linux cleanup - fast termination without waiting
                        try:
                            # Send SIGTERM and SIGKILL quickly without waiting
                            process.terminate()
                            
                            # Give a tiny moment then force kill
                            await asyncio.sleep(0.01)
                            process.kill()
                            
                            # Don't wait for process.wait() as it can hang
                            # Let the OS cleanup the zombie process
                                    
                        except ProcessLookupError:
                            # Process already terminated during cleanup
                            pass
                        
                except ProcessLookupError:
                    # Process already exited, which is fine
                    pass
                except Exception as e:
                    logger.warning(f"Error during process cleanup: {e}")
                finally:
                    # Clean up streams - but only if they're still open
                    # Process termination should have closed them already
                    try:
                        await read_stream.aclose()
                    except:
                        pass
                    try:
                        await write_stream.aclose()
                    except:
                        pass
                    try:
                        await read_stream_writer.aclose()
                    except:
                        pass
                    try:
                        await write_stream_reader.aclose()
                    except:
                        pass


def create_clickup_mcp_server():
    """Create ClickUp MCP server"""
    # Validate environment variables
    api_key = os.environ.get('CLICKUP_API_KEY')
    team_id = os.environ.get('CLICKUP_TEAM_ID')
    
    if not api_key:
        raise ValueError("❌ CLICKUP_API_KEY environment variable is not set")
    
    if not team_id:
        raise ValueError("❌ CLICKUP_TEAM_ID environment variable is not set")
    
    try:
        server = FixedMCPServerStdio(  
            'npx',
            args=[
                '-y',
                '@taazkareem/clickup-mcp-server@latest'
            ],
            env={
                'CLICKUP_API_KEY': api_key,
                'CLICKUP_TEAM_ID': team_id,
            },
            timeout=60.0  # Increase timeout for npx download and server startup
        )
        return server
    except Exception as e:
        logger.error(f"❌ Failed to create ClickUp MCP server: {e}")
        raise

# Create the server instance
MCPServerClickup = create_clickup_mcp_server()