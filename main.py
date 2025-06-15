import os
import asyncio
import logging
import signal
import sys

from dotenv import load_dotenv

from src import db_connection
from src.agent import create_clickup_agent

load_dotenv()

def setup_logging():
    """Configure logging with clean output"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Silence noisy loggers
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def main():
    """Main application entry point"""
    print("🚀 Starting ClickUp Agent...")
    
    try:
        print("📝 Connecting to database...")
        await db_connection.connect()
        
        print("🤖 Creating agent...")
        clickup_agent = create_clickup_agent()
        
        print("▶️  Running agent...")
        result = await clickup_agent.run(
            user_input="get workspace hierarchy",
            user_id="(123)",
        )
        
        print("📄 Getting response...")
        response = await clickup_agent.get_agent_response(result)
        
        print("\n=== AGENT RESPONSE ===")
        print(response)
        print("=== END RESPONSE ===")
        
        print("✅ Task completed successfully")
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        raise
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise
    finally:
        print("🧹 Cleaning up...")
        try:
            await db_connection.disconnect()
            
            # Give time for MCP server processes to terminate properly
            await asyncio.sleep(0.5)
            
            # Cancel any remaining tasks
            tasks = [task for task in asyncio.all_tasks() if not task.done() and task is not asyncio.current_task()]
            if tasks:
                for task in tasks:
                    if not task.cancelled():
                        task.cancel()
                try:
                    await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=3.0)
                except asyncio.TimeoutError:
                    logger.warning("Some tasks took too long to cancel")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        
        print("✅ Done")
        # Final exit to ensure no hanging processes
        os._exit(0)
        

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.warning(f"Received signal {signum}, initiating graceful shutdown...")
    sys.exit(0)

if __name__ == '__main__':
    setup_logging()
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}", exc_info=True)
        sys.exit(1)