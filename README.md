# MCP Server with OAuth 2.1 Authentication (Entra ID)

A Model Context Protocol (MCP) server implementation with OAuth 2.1 authentication using Microsoft Entra ID (formerly Azure Active Directory).

## Features

- ✅ OAuth 2.1 authentication with Microsoft Entra ID
- ✅ JWT token validation with signature verification
- ✅ PKCE support for enhanced security
- ✅ Protected API endpoints
- ✅ FastAPI integration
- ✅ Comprehensive error handling and logging
- ✅ Development mode (auth can be disabled)

## Prerequisites

- Python 3.8 or higher
- Microsoft Entra ID (Azure AD) tenant
- Registered application in Entra ID

## Entra ID Setup

### 1. Register an Application in Entra ID

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Microsoft Entra ID** > **App registrations**
3. Click **New registration**
4. Fill in the details:
   - **Name**: MCP Server (or your preferred name)
   - **Supported account types**: Choose based on your requirements
   - **Redirect URI**: Leave blank for now (or add your callback URL)
5. Click **Register**

### 2. Configure Application

After registration, note down:
- **Application (client) ID**
- **Directory (tenant) ID**

#### Create a Client Secret

1. In your app registration, go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description and select expiration
4. Click **Add**
5. **Copy the secret value immediately** (you won't be able to see it again)

#### Configure API Permissions

1. Go to **API permissions**
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Choose **Delegated permissions** or **Application permissions** based on your needs
5. Add required permissions (e.g., `User.Read`)
6. Click **Add permissions**
7. Click **Grant admin consent** (if you have admin rights)

#### Expose an API (Optional, for custom scopes)

1. Go to **Expose an API**
2. Click **Add a scope**
3. Set the **Application ID URI** (default: `api://{client-id}`)
4. Add scopes as needed

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd Oauth_MCP
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example environment file:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edit `.env` file with your Entra ID configuration:

```env
# Entra ID Configuration
AZURE_TENANT_ID=your-tenant-id-here
AZURE_CLIENT_ID=your-client-id-here
AZURE_CLIENT_SECRET=your-client-secret-here

# OAuth 2.1 Configuration
AZURE_AUTHORITY=https://login.microsoftonline.com/your-tenant-id-here
AZURE_SCOPE=api://your-client-id-here/.default

# Token validation settings
TOKEN_AUDIENCE=api://your-client-id-here
TOKEN_ISSUER=https://login.microsoftonline.com/your-tenant-id-here/v2.0

# Server Configuration
PORT=10000
ENVIRONMENT=production

# Enable/disable authentication
ENABLE_AUTH=true
```

## Running the Server

### Production Mode (with authentication)

```bash
python main.py
```

The server will start on `http://localhost:10000` with authentication enabled.

### Development Mode (without authentication)

For local development without authentication:

1. Set `ENABLE_AUTH=false` in your `.env` file
2. Run the server:

```bash
python main.py
```

⚠️ **Warning**: Never disable authentication in production!

## Usage

### Getting an Access Token

#### Using Python (Client Credentials Flow)

```python
import msal

tenant_id = "your-tenant-id"
client_id = "your-client-id"
client_secret = "your-client-secret"
authority = f"https://login.microsoftonline.com/{tenant_id}"
scope = [f"api://{client_id}/.default"]

app = msal.ConfidentialClientApplication(
    client_id,
    authority=authority,
    client_credential=client_secret,
)

result = app.acquire_token_for_client(scopes=scope)

if "access_token" in result:
    access_token = result["access_token"]
    print(f"Token: {access_token}")
else:
    print(f"Error: {result.get('error_description')}")
```

#### Using cURL (with existing token)

```bash
# Health check (no auth required)
curl http://localhost:10000/health

# Protected endpoint - MCP echo
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     http://localhost:10000/echo

# Get user info
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     http://localhost:10000/me
```

### Making Authenticated Requests

```python
import requests

# Your access token from Entra ID
access_token = "eyJ0eXAiOiJKV1QiLCJhbGc..."

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Call protected MCP endpoint
response = requests.post(
    "http://localhost:10000/echo",
    headers=headers,
    json={"jsonrpc": "2.0", "method": "tools/call", "params": {...}}
)

print(response.json())
```

## API Endpoints

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/health` | GET | No | Health check endpoint |
| `/echo` | POST | Yes | MCP protocol endpoint |
| `/me` | GET | Yes | Get current user info |
| `/docs` | GET | No | OpenAPI documentation |

## Authentication Flow

1. **Client requests token** from Entra ID using client credentials
2. **Entra ID validates** the client credentials
3. **Entra ID issues** a JWT access token
4. **Client sends request** to MCP server with `Authorization: Bearer <token>` header
5. **Server validates token**:
   - Verifies signature using JWKS
   - Checks expiration
   - Validates audience and issuer
6. **Server processes** the request if token is valid
7. **Server returns** response

## Security Best Practices

### ✅ Do's

- Always use HTTPS in production
- Store secrets in environment variables or Azure Key Vault
- Rotate client secrets regularly
- Use least-privilege principle for API permissions
- Enable logging and monitoring
- Set appropriate token expiration times
- Validate tokens on every request

### ❌ Don'ts

- Never commit `.env` files to version control
- Never disable authentication in production
- Never expose client secrets in client-side code
- Never share tokens or credentials
- Don't use the same credentials across environments

## Troubleshooting

### Token Validation Errors

**Error**: `Invalid token audience`

**Solution**: Ensure `TOKEN_AUDIENCE` in `.env` matches the `aud` claim in your token.

---

**Error**: `Invalid token issuer`

**Solution**: Verify `TOKEN_ISSUER` matches the `iss` claim (usually `https://login.microsoftonline.com/{tenant-id}/v2.0`).

---

**Error**: `Token has expired`

**Solution**: Request a new token from Entra ID.

### Connection Issues

**Error**: `Cannot connect to server`

**Solution**: 
- Check if the server is running
- Verify the port is not in use
- Check firewall settings

### Authentication Issues

**Error**: `Missing authorization header`

**Solution**: Include the `Authorization: Bearer <token>` header in your requests.

## Development

### Project Structure

```
Oauth_MCP/
├── main.py              # FastAPI application with protected endpoints
├── math_server.py       # MCP server implementation
├── auth.py              # OAuth 2.1 authentication module
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment configuration
├── .env                 # Your environment configuration (git-ignored)
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

### Adding New Protected Endpoints

```python
from fastapi import Depends
from auth import verify_token

@app.get("/my-endpoint")
async def my_endpoint(token_data: dict = Depends(verify_token)):
    # token_data contains the decoded JWT claims
    user_id = token_data.get("sub")
    return {"message": f"Hello user {user_id}"}
```

### Testing

```bash
# Run with authentication disabled for testing
ENABLE_AUTH=false python main.py

# Or set in .env file
# ENABLE_AUTH=false
```

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `AZURE_TENANT_ID` | Yes | Your Entra ID tenant ID | `12345678-1234-1234-1234-123456789abc` |
| `AZURE_CLIENT_ID` | Yes | Application (client) ID | `87654321-4321-4321-4321-cba987654321` |
| `AZURE_CLIENT_SECRET` | Yes* | Client secret value | `your-secret-value` |
| `AZURE_AUTHORITY` | No | Authority URL | `https://login.microsoftonline.com/{tenant-id}` |
| `AZURE_SCOPE` | No | Default scope | `api://{client-id}/.default` |
| `TOKEN_AUDIENCE` | No | Expected audience claim | `api://{client-id}` |
| `TOKEN_ISSUER` | No | Expected issuer claim | `https://login.microsoftonline.com/{tenant-id}/v2.0` |
| `PORT` | No | Server port | `10000` |
| `ENABLE_AUTH` | No | Enable/disable auth | `true` or `false` |

*Required for production, can be omitted if using managed identity