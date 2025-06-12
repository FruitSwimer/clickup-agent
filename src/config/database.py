from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase


class DatabaseSettings(BaseSettings):
    mongodb_url: str = Field(
        default="mongodb://localhost:27017",
        alias="MONGO_URI",
        description="MongoDB connection URL"
    )
    database_name: str = Field(
        default="axle_agents",
        env="DATABASE_NAME",
        description="Database name"
    )
    raw_messages_collection: str = Field(
        default="raw_messages",
        env="RAW_MESSAGES_COLLECTION",
        description="Collection name for raw messages"
    )
    agent_sessions_collection: str = Field( 
        default="agent_sessions",
        env="AGENT_SESSIONS_COLLECTION",
        description="Collection name for agent sessions"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


class DatabaseConnection:
    _instance: Optional['DatabaseConnection'] = None
    _client: Optional[AsyncMongoClient] = None
    _database: Optional[AsyncDatabase] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.settings = DatabaseSettings()
    
    async def connect(self) -> None:
        if self._client is None:
            self._client = AsyncMongoClient(self.settings.mongodb_url)
            self._database = self._client[self.settings.database_name]
    
    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
            self._database = None
    
    @property
    def database(self) -> AsyncDatabase:
        if self._database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._database
    
    @property
    def raw_messages_collection(self):
        return self.database[self.settings.raw_messages_collection]
    
    @property
    def agent_sessions_collection(self):
        return self.database[self.settings.agent_sessions_collection]


db_connection = DatabaseConnection()