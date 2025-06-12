import os
import asyncio

from pydantic import BaseModel, Field
from dataclasses import dataclass
from dotenv import load_dotenv

from src import db_connection
from src.agent import create_clickup_agent

load_dotenv()


async def main():
    await db_connection.connect()
    clickup_agent = create_clickup_agent()
    result = await clickup_agent.run(
        user_input="get workspace hiercahy",
        user_id="12345",
    )
    response = await clickup_agent.get_agent_response(result)
    print(response)

if __name__ == '__main__':
    asyncio.run(main())