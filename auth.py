"""
OAuth 2.1 Authentication Module for MCP Server with Entra ID (Azure AD)

This module provides OAuth 2.1 authentication and authorization using Microsoft Entra ID.
It implements token validation, JWT verification, and FastAPI middleware for protecting endpoints.
"""

import os
import logging
from typing import Optional, Dict, Any
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Request
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Entra ID Configuration
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
TOKEN_AUDIENCE = os.getenv("TOKEN_AUDIENCE", f"api://{AZURE_CLIENT_ID}")
TOKEN_ISSUER = os.getenv("TOKEN_ISSUER", f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/v2.0")
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "true").lower() == "true"


class EntraIDAuth:
    """
    Entra ID OAuth 2.1 Authentication Handler
    
    This class handles token validation for Microsoft Entra ID.
    It validates JWT tokens using JWKS (JSON Web Key Set).
    """
    
    def __init__(self):
        self.tenant_id = AZURE_TENANT_ID
        self.client_id = AZURE_CLIENT_ID
        self.jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
        self.jwks_client = None
        
        if ENABLE_AUTH:
            self._validate_config()
            self.jwks_client = PyJWKClient(self.jwks_uri)
            logger.info("Entra ID authentication initialized successfully")
        else:
            logger.warning("Authentication is DISABLED. This should only be used in development!")
    
    def _validate_config(self):
        """Validate that all required configuration is present"""
        if not all([self.tenant_id, self.client_id]):
            raise ValueError(
                "Missing required Entra ID configuration. "
                "Please set AZURE_TENANT_ID, AZURE_CLIENT_ID in environment variables."
            )
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a JWT token from Entra ID
        
        This method performs comprehensive token validation including:
        - Signature verification using JWKS
        - Expiration check
        - Audience validation
        - Issuer validation (supports both v1.0 and v2.0 tokens)
        
        Args:
            token: JWT access token to validate
            
        Returns:
            dict: Decoded token claims if valid
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            # Get the signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode without validation first to check issuer format
            unverified_token = jwt.decode(token, options={"verify_signature": False})
            actual_issuer = unverified_token.get("iss")
            
            # Support both v1.0 and v2.0 token issuers
            # v1.0: https://sts.windows.net/{tenant}/
            # v2.0: https://login.microsoftonline.com/{tenant}/v2.0
            valid_issuers = [
                f"https://sts.windows.net/{self.tenant_id}/",
                f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
            ]
            
            # # Token verification using scope
            # if unverified_token.get("scp") == "user_read":
            #     print("token verified using scope")
            #     return unverified_token
            # else:
            #     return "Invalid token"z
            
            # Decode and validate the token
            decoded_token = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=TOKEN_AUDIENCE,
                issuer=valid_issuers,  # Accept both v1.0 and v2.0
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                }
            )
            
            logger.info(f"Token validated successfully for subject: {decoded_token.get('sub')}")
            # logger.info(f"Token information: {decoded_token}")
            return decoded_token
            
        except jwt.ExpiredSignatureError:
            logger.error("Token has expired")
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidAudienceError:
            logger.error("Invalid token audience")
            raise HTTPException(status_code=401, detail="Invalid token audience")
        except jwt.InvalidIssuerError:
            logger.error(f"Invalid token issuer. Expected one of {valid_issuers}, got {actual_issuer}")
            raise HTTPException(status_code=401, detail=f"Invalid token issuer")
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            raise HTTPException(status_code=401, detail="Token validation failed")


# Global authentication instance
auth_handler = EntraIDAuth()


class AuthMiddleware:
    """
    FastAPI middleware for OAuth 2.1 authentication
    
    This middleware automatically validates tokens for all requests to protected paths.
    """
    
    def __init__(self, excluded_paths: list[str] = None):
        """
        Initialize the authentication middleware
        
        Args:
            excluded_paths: List of path prefixes to exclude from authentication
        """
        self.excluded_paths = excluded_paths or ["/docs", "/redoc", "/openapi.json", "/health"]
    
    async def __call__(self, request: Request, call_next):
        """
        Process the request through the authentication middleware
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in the chain
            
        Returns:
            Response from the next handler
        """
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Skip if authentication is disabled
        if not ENABLE_AUTH:
            return await call_next(request)
        
        # Check for authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "unauthorized",
                    "message": "Missing or invalid authorization header",
                    "instructions": {
                        "how_to_get_token": "Use client credentials flow to acquire a token from Microsoft Entra ID",
                        "token_endpoint": f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token",
                        "required_scopes": f"api://{AZURE_CLIENT_ID}/user_read",
                        "usage": "Include the token in the Authorization header as: Bearer <your_access_token>"
                    }
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract and validate token
        token = auth_header.split(" ")[1]
        try:
            decoded_token = auth_handler.validate_token(token)
            # Add user info to request state
            request.state.user = decoded_token
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication failed")
        
        return await call_next(request)


def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Get the current authenticated user from request state
    
    Args:
        request: FastAPI request object
        
    Returns:
        dict: User information from token claims
    """
    if not ENABLE_AUTH:
        return {"sub": "development-user", "name": "Development User"}
    
    if not hasattr(request.state, "user"):
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    return request.state.user
