import os
from google.adk import Agent

# Define the Agent
# We use 'anthropic/' as a prefix so ADK's extensions know which provider to use.
root_agent = Agent(
    name="claude_assistant",
    model="anthropic/claude-sonnet-4-6", # Replace with your preferred Claude model
    instruction="You are a helpful AI assistant. Please provide short on sentence answers.",
)
    
