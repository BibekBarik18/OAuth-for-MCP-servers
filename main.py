"""
MCP Server with OAuth 2.1 Authentication using Entra ID

This is the main FastAPI application that hosts the MCP server with
OAuth 2.1 authentication protection via Microsoft Entra ID.
"""

import contextlib
import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from math_server import mcp
from auth import get_current_user, ENABLE_AUTH, AuthMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting MCP Server with OAuth 2.1 authentication")
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield
    logger.info("Shutting down MCP Server")


# Initialize FastAPI application
app = FastAPI(
    title="MCP Server with OAuth 2.1",
    description="MCP Server protected by Microsoft Entra ID OAuth 2.1 authentication",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add authentication middleware to protect all endpoints except excluded paths
if ENABLE_AUTH:
    auth_middleware = AuthMiddleware(
        excluded_paths=["/health", "/docs",]
    )
    app.middleware("http")(auth_middleware)
    logger.info("Authentication middleware enabled")


# Health check endpoint (public)
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "MCP Server",
        "authentication": "enabled" if ENABLE_AUTH else "disabled"
    }


# MCP endpoint - protected by authentication middleware
app.mount("/echo", mcp.streamable_http_app())


# User info endpoint - protected by authentication middleware
@app.get("/me", tags=["User"])
async def get_user_info(request: Request):
    """Get current authenticated user information from token claims"""
    token_data = get_current_user(request)
    return {
        "user_id": token_data.get("sub"),
        "name": token_data.get("name"),
        "email": token_data.get("email", token_data.get("upn", token_data.get("preferred_username"))),
        "roles": token_data.get("roles", []),
        "scopes": token_data.get("scp", "").split() if "scp" in token_data else []
    }


# Exception handler for unauthorized access
@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    """Handle unauthorized access attempts"""
    return JSONResponse(
        status_code=401,
        content={
            "error": "unauthorized",
            "message": "Valid authentication required. Please provide a valid bearer token.",
            "details": str(exc.detail) if hasattr(exc, 'detail') else None
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


PORT = int(os.getenv("PORT", 10000))

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on port {PORT}")
    logger.info(f"Authentication: {'ENABLED' if ENABLE_AUTH else 'DISABLED'}")
    
    if not ENABLE_AUTH:
        logger.warning("=" * 80)
        logger.warning("WARNING: Authentication is DISABLED!")
        logger.warning("This should only be used in development environments.")
        logger.warning("Set ENABLE_AUTH=true in .env for production use.")
        logger.warning("=" * 80)
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=10000,
        log_level="info"
    )
