# app.py
import chainlit as cl
from dotenv import load_dotenv
import os
from fastmcp.client import Client as MCPClient
from fastmcp.client.transports import StreamableHttpTransport
from agents import Agent, ModelSettings, function_tool, Runner
import logging
from typing import Dict, Any
from chainlit import oauth_providers
from chainlit.config import config


# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Generic tool runner from MCP client
async def run_tool(client: MCPClient, tool_name: str, params: Dict[str, Any], progress_handler=None):
    """Run a specific tool on the MCP server"""
    try:
        async with client:
            result = await client.call_tool(tool_name, params, progress_handler=progress_handler)
            logger.info(f"Result from tool '{tool_name}': {result}")
            return result
    except Exception as e:
        logger.error(f"Error calling tool '{tool_name}': {e}")
        return None

# Create OpenAI Agent with tools
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
        
    
    try:
        agent = Agent(
            name="MCP Agent",
            instructions="""You are a helpful assistant. You can do chitchat, reverse strings, and generate random numbers.""",
            model="gpt-4.1-nano",
            tools=[reverse_tool, random_int_tool],
        )
        logger.info("Agent created successfully")
        return agent
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        return None

@cl.on_chat_start
async def start():
    user = cl.user_session.get("user")
    token = cl.user_session.get("token")

    # create agent and store it in user session
    agent = await create_agent()
    cl.user_session.set("agent", agent)


    if not agent:
        await cl.Message("Failed to create agent.").send()
        return
    
    await cl.Message(f"Hello, {user}!").send()
    await cl.Message(f"Token: {token}").send()

@cl.on_message
async def handle(msg: cl.Message):
    await cl.Message("You said: " + msg.content).send()
    agent = cl.user_session.get("agent")
    if not agent:
        await cl.Message("No agent available.").send()
        return
    else:
        try:
            # Run the agent with the message content
            response = await Runner.run(agent, msg.content)
            await cl.Message(f"Agent response: {response.final_output}").send()
        except Exception as e:
            await cl.Message(f"Error running agent: {e}").send()

@cl.oauth_callback
def auth_callback(provider_id: str, token: str, raw_user_data, default_app_user):
    if provider_id == "azure-ad":
        # Ensure the user object has an identifier property
        user = default_app_user
        if not hasattr(user, "identifier"):
            # fallback: try to set identifier from raw_user_data
            identifier = raw_user_data.get("email") or raw_user_data.get("id") or "unknown"
            user.identifier = identifier
        cl.user_session.set("user", user)
        cl.user_session.set("token", token)
        return user  # grant access
    return None
