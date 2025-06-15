import logging
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

logger = logging.getLogger(__name__)


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
        logger.debug(f"Database settings initialized: {self.settings.mongodb_url}")
    
    async def connect(self) -> None:
        """Connect to MongoDB"""
        if self._client is None:
            try:
                logger.debug("DEBUG: Creating AsyncMongoClient")
                self._client = AsyncMongoClient(self.settings.mongodb_url)
                logger.debug("DEBUG: Getting database reference")
                self._database = self._client[self.settings.database_name]
                
                # Test the connection
                logger.debug("DEBUG: Testing database connection with ping")
                await self._client.admin.command('ping')
                print("  ✅ Database connected")
                logger.debug("DEBUG: Database ping successful")
                
            except Exception as e:
                logger.error(f"❌ Database connection failed: {e}")
                logger.debug("DEBUG: Exception during database connection")
                raise
    
    async def disconnect(self) -> None:
        """Disconnect from MongoDB"""
        if self._client:
            try:
                logger.debug("DEBUG: About to close MongoDB client")
                # Close MongoDB client properly
                await self._client.close()
                logger.debug("DEBUG: MongoDB client closed")
                self._client = None
                self._database = None
                print("  ✅ Database disconnected")
                logger.debug("DEBUG: Database disconnect completed")
            except Exception as e:
                logger.error(f"❌ Database disconnect error: {e}")
                logger.debug("DEBUG: Exception during database disconnect")
    
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