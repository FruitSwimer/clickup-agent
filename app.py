import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from src import db_connection
from src.agent import create_clickup_agent

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    user_input: str = Field(..., description="User's message to the agent")
    user_id: str = Field(..., description="Unique user identifier")


class ChatResponse(BaseModel):
    success: bool = Field(..., description="Whether the request was successful")
    message: Optional[str] = Field(None, description="Response message")
    error: Optional[str] = Field(None, description="Error message if any")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status")
    database: str = Field(..., description="Database connection status")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up FastAPI application...")
    try:
        await db_connection.connect()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise
    
    yield
    
    logger.info("Shutting down FastAPI application...")
    await db_connection.disconnect()
    logger.info("Database connection closed")


app = FastAPI(
    title="ClickUp Agent API",
    description="Production-ready API for interacting with ClickUp agent",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error occurred"
        }
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check the health status of the API and its dependencies."""
    try:
        db_status = "connected" if db_connection._client else "disconnected"
    except Exception:
        db_status = "error"
    
    return HealthResponse(
        status="healthy",
        database=db_status
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message using the ClickUp agent.
    
    Args:
        request: ChatRequest containing user_input and user_id
        
    Returns:
        ChatResponse with the agent's response or error message
    """
    logger.info(f"Chat request from user {request.user_id}: {request.user_input[:50]}...")
    
    try:
        clickup_agent = create_clickup_agent()
        
        result = await clickup_agent.run(
            user_input=request.user_input,
            user_id=request.user_id
        )
        response = await clickup_agent.get_agent_response(result)
        logger.info(f"Successfully processed chat request for user {request.user_id}")
        
        return ChatResponse(
            success=True,
            message=str(response) if result else "Agent processed the request successfully"
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request for user {request.user_id}: {e}", exc_info=True)
        
        return ChatResponse(
            success=False,
            error=f"Failed to process chat request: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT", "production") == "development",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )