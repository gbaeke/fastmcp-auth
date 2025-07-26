#!/usr/bin/env python3
"""
MCP Client to connect to the authenticated MCP server and list available tools
"""

import os
import logging
import asyncio
import sys
from typing import Dict, Any
import click
import msal
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastmcp.client import Client as MCPClient
from fastmcp.client.transports import StreamableHttpTransport

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Azure Entra ID configuration
TENANT_ID = "484588df-21e4-427c-b2a5-cc39d6a73281"  # Tenant ID
CLIENT_ID = "cdff3d96-909d-4685-b1d1-3846330ad4db"  # Web app client ID
API_SCOPE = "api://f9ca7d53-fd9c-4e71-83f1-55f4644a75d6/execute"  # API scope
API_AUDIENCE = "api://f9ca7d53-fd9c-4e71-83f1-55f4644a75d6"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

# Token cache file
cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token_cache.json")


def load_cache():
    """Load the token cache from file"""
    try:
        cache = msal.SerializableTokenCache()
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                cache_data = f.read()
                if cache_data:
                    cache.deserialize(cache_data)
                    logger.info(f"Token cache loaded from {cache_file}")
        else:
            logger.info(f"Token cache file not found at {cache_file}, creating new cache")
        return cache
    except Exception as e:
        logger.error(f"Error loading token cache: {e}")
        return msal.SerializableTokenCache()


def save_cache(cache):
    """Save the token cache to file"""
    if cache.has_state_changed:
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            
            # Write the cache to file
            with open(cache_file, "w") as f:
                f.write(cache.serialize())
            
            logger.info(f"Token cache saved to {cache_file}")
            
            # Verify file permissions (on Unix/Linux/macOS)
            if os.name != "nt":  # Not Windows
                os.chmod(cache_file, 0o600)  # Read/write for owner only
                
        except Exception as e:
            logger.error(f"Error saving token cache: {e}")


def get_token():
    """Get an access token for the API"""
    # Initialize token cache
    cache = load_cache()
    
    # Create MSAL app
    app = msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache
    )
    
    # Check if there's a token in cache
    accounts = app.get_accounts()
    if accounts:
        logger.info(f"Found {len(accounts)} cached account(s)")
        # Try to get token silently
        result = app.acquire_token_silent([API_SCOPE], account=accounts[0])
        if result:
            logger.info("Token acquired silently from cache")
            save_cache(cache)
            return result
        else:
            logger.info("Silent token acquisition failed, need interactive auth")
    
    # If no token in cache or silent acquisition fails, acquire token interactively
    flow_started = app.initiate_device_flow(scopes=[API_SCOPE])
    if "user_code" not in flow_started:
        logger.error(f"Failed to create device flow: {flow_started.get('error')}")
        logger.error(f"Error description: {flow_started.get('error_description')}")
        return None
    
    # Display instructions to user
    logger.info(flow_started["message"])
    
    # Poll for token
    result = app.acquire_token_by_device_flow(flow_started)
    
    # Save token cache
    save_cache(cache)
    
    return result


def get_jwt_token():
    """
    Get just the JWT token string for programmatic use.
    
    Returns:
        str: The access token string, or None if acquisition fails
    """
    result = get_token()
    if "access_token" in result:
        return result["access_token"]
    else:
        logger.error(f"Failed to obtain token: {result.get('error')}")
        logger.error(f"Error description: {result.get('error_description')}")
        return None
    
async def my_progress_handler(
    progress: float, 
    total: float | None, 
    message: str | None
) -> None:
    if total is not None:
        percentage = (progress / total) * 100
        print(f"Progress: {percentage:.1f}% - {message or ''}")
    else:
        print(f"Progress: {progress} - {message or ''}")



async def connect_mcp(skip_auth: bool = False):
    """Connect to the MCP server and list tools"""
    
    # Initialize headers dictionary
    headers = {}
    
    # Add authentication unless skipped
    if not skip_auth:
        # Get a JWT token for authentication
        token = get_jwt_token()
        if not token:
            logger.error("Failed to get JWT token")
            return
        
        logger.info("Successfully obtained JWT token")
        logger.info(f"JWT Token: {token}")
        
        # Add authorization header
        headers["Authorization"] = f"Bearer {token}"
    else:
        logger.info("Skipping authentication as requested")
    
    # Create an MCP client with authentication header
    # For HTTP transport, use StreamableHttpTransport
    transport_url = "http://localhost:8000/mcp/"  # Match the server URL
    
    # Create the transport with headers (may or may not include auth)
    transport = StreamableHttpTransport(
        url=transport_url,
        headers=headers
    )
    
    # Create the client with the streamable transport
    client = MCPClient(transport=transport, progress_handler=my_progress_handler)
    
    try:
        logger.info("Connecting to the MCP server...")
        
        # Use the client as an async context manager
        async with client:
            # List available tools on the server
            tools = await client.list_tools()
            logger.info(f"Found {len(tools)} tools on the server")
            
            # Print each tool and its details
            for tool in tools:
                logger.info(f"Tool: {tool.name}")
                logger.info(f"  Description: {tool.description}")
                logger.info("---")
            
            # Try calling the reverse_tool
            logger.info("Calling reverse_tool...")
            result = await client.call_tool("reverse_tool", {"query": "Hello from MCP client!"})
            logger.info(f"Result: {result}")
        
    except Exception as e:
        logger.error(f"Error connecting to MCP server: {e}")


@click.command()
@click.option('-n', '--no-auth', is_flag=True, help='Skip authentication and connect without JWT token')
def main(no_auth):
    """Run the MCP client with optional authentication skipping."""
    asyncio.run(connect_mcp(skip_auth=no_auth))


if __name__ == "__main__":
    main()  # This invokes the Click command
