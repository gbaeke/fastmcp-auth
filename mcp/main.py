#!/usr/bin/env python3
"""
Simple MCP Server with one reverse tool and Azure Entra ID authentication
"""

import logging
import os
from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.server.auth import BearerAuthProvider
from fastmcp.server.dependencies import get_access_token, AccessToken
import asyncio
import random

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Azure Entra ID configuration
TENANT_ID = "484588df-21e4-427c-b2a5-cc39d6a73281"
CLIENT_ID = "f9ca7d53-fd9c-4e71-83f1-55f4644a75d6"
# API audience can be in multiple formats, so we'll define both common ones
API_AUDIENCE = f"api://{CLIENT_ID}"

# Azure Entra ID JWKS endpoint
JWKS_URI = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"

# Configure Bearer Token authentication for Azure Entra ID
logger.info("Configuring Bearer Token authentication with audience: %s", API_AUDIENCE)
auth = BearerAuthProvider(
    jwks_uri=JWKS_URI,
    issuer=f"https://sts.windows.net/{TENANT_ID}/",  # Match the token's issuer format in the API
    algorithm="RS256",  # Azure Entra ID uses RS256
    audience=API_AUDIENCE,  # required audience
    required_scopes=["execute"]  # Optional: add required scopes if needed
)

# Create the MCP server with authentication
mcp = FastMCP("Simple Reverse Server with Azure Auth", auth=auth)

# Without authentication, just for testing
# mcp = FastMCP("Simple Reverse Server with Azure Auth")


@mcp.tool()
async def reverse_tool(ctx: Context, query: str) -> dict:
    """
    Reverse the given query string.
    
    Args:
        ctx: FastMCP context
        query: The string to reverse
        
    Returns:
        The reversed query string
    """
    logger.info(f"Reverse tool called with query: {query}")

    # Pretend to do work
    # Simulate processing time and report progress
    total_seconds = 5
    for i in range(total_seconds):
        await ctx.report_progress(progress=i, total=total_seconds)
        await asyncio.sleep(1)
    await ctx.report_progress(progress=total_seconds, total=total_seconds)

    
    # Simply reverse the query string
    reversed_query = query[::-1]

    return {"reversed_query": reversed_query}

@mcp.tool()
async def random_number_tool(ctx: Context, min: int, max: int) -> dict:
    """
    Generate a random integer between min and max (inclusive).

    Args:
        ctx: FastMCP context
        min: Minimum value (inclusive)
        max: Maximum value (inclusive)

    Returns:
        A dictionary with the generated random number
    """
    logger.info(f"Random number tool called with min: {min}, max: {max}")
    if min > max:
        raise ValueError("min must be less than or equal to max")
    number = random.randint(min, max)
    return {"random_number": number}
    
def main():
    """Main entry point for the FastMCP server"""
    logger.info("Starting authenticated FastMCP server...")
    logger.info(f"Azure Tenant ID: {TENANT_ID}")
    logger.info(f"Azure Client ID: {CLIENT_ID}")
    logger.info(f"JWKS URI: {JWKS_URI}")
    
    try:
        # Run the server with HTTP transport (required for authentication)
        # Authentication only works with HTTP-based transports
        mcp.run(
            transport="streamable-http",  # Use HTTP transport for authentication
            host="0.0.0.0",
            port=8000
        )
    except Exception as e:
        logger.error(f"Error running server: {e}")
        raise


if __name__ == "__main__":
    main()