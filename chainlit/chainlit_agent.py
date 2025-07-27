# app.py
import chainlit as cl
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

@cl.on_chat_start
async def start():
    user = cl.user_session.get("user")
    await cl.Message(f"Hello, {user.identifier}!").send()

@cl.on_message
async def handle(msg: cl.Message):
    await cl.Message("You said: " + msg.content).send()

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
        return user  # grant access
    return None
