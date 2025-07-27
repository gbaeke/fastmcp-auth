"""
Agent that uses MCP to connect to tools

Required environment variables in .env:
- TENANT_ID: Azure Entra ID tenant ID
- CLIENT_ID: Azure Entra ID client ID
- API_SCOPE: API scope for authentication
- API_AUDIENCE: API audience (optional)
"""

import os
import logging
import asyncio
import sys
from typing import Dict, Any
import click
import msal
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.live import Live


from dotenv import load_dotenv
from fastmcp.client import Client as MCPClient
from fastmcp.client.transports import StreamableHttpTransport
from agents import Agent, ModelSettings, function_tool, Runner


# Set up logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Set up Rich console
console = Console()

# Load environment variables from .env file in the same folder
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=env_path)

# Azure Entra ID configuration from environment variables
TENANT_ID = os.getenv("TENANT_ID")  # Tenant ID
CLIENT_ID = os.getenv("CLIENT_ID")  # Web app client ID
API_SCOPE = os.getenv("API_SCOPE")  # API scope
API_AUDIENCE = os.getenv("API_AUDIENCE")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

# Validate required environment variables
if not all([TENANT_ID, CLIENT_ID, API_SCOPE]):
    console.print(Panel(
        "[bold red]Missing required environment variables in .env file.\n"
        "Please ensure TENANT_ID, CLIENT_ID, and API_SCOPE are defined.",
        title="Configuration Error",
        border_style="red"
    ))
    logger.error("Missing required environment variables. Check .env file.")
    if not TENANT_ID:
        logger.error("TENANT_ID is missing")
    if not CLIENT_ID:
        logger.error("CLIENT_ID is missing")
    if not API_SCOPE:
        logger.error("API_SCOPE is missing")

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
    with console.status("[bold green]Acquiring authentication token...") as status:
        result = get_token()
    
    if "access_token" in result:
        console.print(Panel("[bold green]✓ Token acquired successfully!", 
                           title="Authentication", 
                           border_style="green"))
        return result["access_token"]
    else:
        console.print(Panel(f"[bold red]✗ Failed to obtain token: {result.get('error')}\n"
                           f"Error description: {result.get('error_description')}", 
                           title="Authentication Error", 
                           border_style="red"))
        logger.error(f"Failed to obtain token: {result.get('error')}")
        logger.error(f"Error description: {result.get('error_description')}")
        return None
    
# Global progress object for tracking tool progress
from rich.live import Live

_progress_live = None
_progress = None
_task_id = None

# Set a throttle to prevent too frequent updates (in seconds)
_progress_throttle = 0.1
_last_update_time = 0

async def my_progress_handler(
    progress: float, 
    total: float | None, 
    message: str | None
) -> None:
    """Handle progress updates for tools (FastMCP specific)"""
    global _progress_live, _progress, _task_id, _last_update_time
    
    # Initialize progress if not already done
    if _progress is None:
        _progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            TextColumn("[bold green]{task.percentage:.1f}%"),
            TextColumn("[yellow]{task.fields[message]}"),
            refresh_per_second=10,  # Limit refresh rate
        )
        _task_id = _progress.add_task("Tool Progress", total=100, message="")
        _progress_live = Live(_progress, console=console, refresh_per_second=5, auto_refresh=False)
        _progress_live.start()
    
    # Get current time for throttling
    current_time = asyncio.get_event_loop().time()
    
    # Throttle updates
    if current_time - _last_update_time < _progress_throttle:
        return
    
    _last_update_time = current_time
    
    if total is not None:
        percentage = (progress / total) * 100
        _progress.update(_task_id, completed=percentage, message=message or "")
    else:
        # Handle indeterminate progress
        _progress.update(_task_id, message=message or "")
    
    # Refresh the live display
    _progress_live.refresh()
        
    # If we've reached 100%, clean up the progress display
    if total is not None and progress >= total:
        _progress_live.stop()
        _progress_live = None
        _progress = None

async def list_tools(client: MCPClient):
    """List available tools on the MCP server"""
    try:
        async with client:
            logger.info("Connected to the MCP server successfully")
       
            with console.status("[bold green]Listing available tools...") as status:
                logger.info("Listing available tools...")
                tools = await client.list_tools()
            
            if tools:
                # Create a table for displaying tools
                table = Table(title=f"Found {len(tools)} MCP Tools")
                table.add_column("Tool Name", style="cyan", no_wrap=True)
                table.add_column("Description", style="green")
                
                for tool in tools:
                    table.add_row(tool.name, tool.description)
                    # Still log for debugging purposes
                    logger.info(f"Tool: {tool.name}")
                    logger.info(f"  Description: {tool.description}")
                    logger.info("---")
                
                console.print(table)
            else:
                console.print("[yellow]No tools found on the MCP server")
            
            return tools
    except Exception as e:
        console.print(f"[bold red]Error listing tools: {e}")
        logger.error(f"Error listing tools: {e}")
        return []
    
async def run_tool(client: MCPClient, tool_name: str, params: Dict[str, Any], progress_handler=None):
    """Run a specific tool on the MCP server"""
    try:
        async with client:
            with console.status(f"[bold blue]Executing tool [cyan]{tool_name}[/cyan]...") as status:
                logger.info(f"Calling tool '{tool_name}' with parameters: {params}")
                result = await client.call_tool(tool_name, params, progress_handler=progress_handler)
            
            console.print(f"[bold green]✓ Tool [cyan]{tool_name}[/cyan] executed successfully!")
            logger.info(f"Result from tool '{tool_name}': {result}")
            return result
    except Exception as e:
        console.print(f"[bold red]✗ Error calling tool '{tool_name}': {e}")
        logger.error(f"Error calling tool '{tool_name}': {e}")
        return None


async def create_agent(client: MCPClient = None):
    """Create agent with OpenAI Agents SDK"""

    @function_tool()
    async def reverse_tool(query: str) -> str:
        """Reverse a string"""

        try:
            result = await run_tool(client, "reverse_tool", {"query": "Hello from MCP client!"}, progress_handler=my_progress_handler)
            logger.info(f"Result from reverse_tool: {result}")
            return result.structured_content
        except Exception as e:
            logger.warning(f"Could not call reverse_tool: {e}")
            return "Error calling reverse_tool"
        
    @function_tool()
    async def random_int_tool(min: int, max: int) -> int:
        """Generate a random integer between min and max (inclusive)"""
        try:
            result = await run_tool(client, "random_number_tool", {"min": min, "max": max})
            logger.info(f"Result from random_number_tool: {result}")
            # Assuming the remote tool returns a dict like {"random_number": value}
            return result.structured_content.get("random_number", None)
        except Exception as e:
            logger.warning(f"Could not call random_number_tool: {e}")
            return "Could not generate random number"
        
    with console.status("[bold magenta]Creating agent...") as status:
        try:
            agent = Agent(
                name="MCP Agent",
                instructions="You are an agent that only responds from tools and never from your own knowledge. You are connected to the MCP server and can call tools.",
                model="gpt-4.1-nano",
                tools=[reverse_tool, random_int_tool],
            )
            console.print("[bold green]✓ Agent created successfully!")
            return agent
        except Exception as e:
            console.print(f"[bold red]✗ Error creating agent: {e}")
            logger.error(f"Error creating agent: {e}")
            return None

async def run_agent(skip_auth: bool = False):
    """Connect to the MCP server and list tools"""
    
    # Initialize headers dictionary
    headers = {}
    
    # Add authentication unless skipped
    if not skip_auth:
        # First check if environment variables are properly loaded
        if not all([TENANT_ID, CLIENT_ID, API_SCOPE]):
            console.print(Panel(
                "[bold red]Cannot authenticate: Missing environment variables.\n"
                "Check that your .env file contains TENANT_ID, CLIENT_ID, and API_SCOPE.",
                title="Authentication Error",
                border_style="red"
            ))
            return
            
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
        console.print("[yellow]Skipping authentication as requested")
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
    client = MCPClient(transport=transport)

    # try to connect to the MCP server
    try:
        with console.status("[bold blue]Connecting to MCP server...") as status:
            logger.info("Connecting to the MCP server...")
            # Use the client as an async context manager
            async with client:
                logger.info("Connected to the MCP server successfully")
        console.print("[bold green]✓ Connected to MCP server")
    except Exception as e:
        console.print(f"[bold red]✗ Error connecting to MCP server: {e}")
        logger.error(f"Error connecting to MCP server: {e}")
        return

    # list tools
    tools = await list_tools(client)

    # just run the tool reverse_tool to test the connection
    try:
        # run with progress handler because reverse_tool is a long-running tool that sends progress updates
        result = await run_tool(client, "reverse_tool", {"query": "Hello from MCP client!"}, progress_handler=my_progress_handler)
        logger.info(f"Result from reverse_tool: {result}")
    except Exception as e:
        logger.warning(f"Could not call reverse_tool: {e}")

    # create an agent
    agent = await create_agent(client)
    if agent:
        logger.info(f"Agent created: {agent.name}")
        
        # Start the agent with nice UI
        prompt = "Reverse this text: 'Hello, MCP!' and generate a random number between 1 and 40."
        console.print(Panel(f"[bold blue]Starting agent with prompt: [white]'{prompt}'", 
                           title="Agent Started", 
                           border_style="blue"))
        
        with console.status("[bold purple]Agent is thinking...") as status:
            result = await Runner.run(agent, prompt)
        
        # Display the agent's response in a nice panel
        console.print(Panel(f"[green]{result.final_output}", 
                           title="Agent Response", 
                           border_style="green"))

@click.command()
@click.option('-n', '--no-auth', is_flag=True, help='Skip authentication and connect without JWT token')
def main(no_auth):
    """Run the MCP client with optional authentication skipping."""
    # Print the location of the .env file for user reference
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    console.print(f"[blue]Using environment configuration from: [white]{env_path}")
    
    asyncio.run(run_agent(skip_auth=no_auth))


if __name__ == "__main__":
    main()  # This invokes the Click command
