import os
from google.adk import Agent
from google.adk.models.lite_llm import LiteLlm  # ADK wrapper for model services such as Ollama and OpenRouter
import urllib.request                           # Import the built-in library for custom curl tool

### Model Provider ###
# Ensure your API key is loaded from your environment
openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")

# Define ANSI escape codes for terminal coloring
GREEN = "\033[92m"
RESET = "\033[0m"

### ----------------------------------- ###
### Callback hooks for agent operations ###
# The ADK automatically passes the current 'agent' and 'context' to these functions.
# You can access agent data from the context.
def log_start_trigger(callback_context):
    # Reset loop counter at the start of every new user turn to manual control agent loop
    callback_context.session.state["loop_count"] = 0

    # Safely convert the user_content to a string and strip whitespace
    user_message = str(getattr(callback_context, 'user_content', '')).strip()
    
    # Exit cleanly if the user types /exit 
    if user_message == '/exit':
        print(f"{GREEN}[TRIGGER LOG]{RESET} Exit command detected! Terminating agent invocation.")
        # Setting this boolean flag to True tells the ADK runtime to stop immediately
        callback_context.end_invocation = True
        return None

    # Otherwise call back function on agent start  
    print(f"{GREEN}[TRIGGER LOG]{RESET} Waking up agent: {callback_context.agent_name}...")
    # Always return None if you just want to observe/log
    return None

# Before tool call trigger
def log_before_tool_trigger(tool, args, tool_context):
    # 'args' is the dictionary of the exact arguments the AI is passing to the tool
    # Retrieve our counter from the session state and increment it
    current_loops = tool_context.session.state.get("loop_count", 0) + 1
    tool_context.session.state["loop_count"] = current_loops
    print(f"{GREEN}[TOOL LOG]{RESET} (Loop {current_loops}/3) AI tool request '{tool.name}' with arg: {args}")

    # Check our hard limit! 
    if current_loops > 3:
        print(f"{GREEN}[TOOL WARNING]{RESET} Exceeded max loop iterations! Force stopping to prevent infinite loop.")
        # Flip the kill switch to immediately end the agent's internal reasoning loop
        tool_context.end_invocation = True

        # We use natural language to force the LLM to break its own ReAct loop!
        # The LLM will read this, realize it is cut off, and formulate a final response.
        return {
            "CRITICAL_SYSTEM_ERROR": "You have exceeded the maximum allowed tool calls. "
                                     "DO NOT call any more tools. You MUST immediately stop "
                                     "and reply to the user with a final summary of what you "
                                     "have learned so far."
        } 
    return None


# End of response
def log_model_finished_trigger(callback_context, llm_response):
    # Check if the LLM's response contains a list of tool/function calls
    # (The exact attribute name depends on your ADK version, usually 'function_calls' or 'tool_calls')
    calls = getattr(llm_response, 'function_calls', []) or getattr(llm_response, 'tool_calls', [])
    
    if calls and len(calls) > 3:
        print(f"{GREEN}[LLM WARNING]{RESET} LLM requested {len(calls)} tool calls. Truncating to 3!")
        
        # Forcefully slice the list down to a maximum of 3
        if hasattr(llm_response, 'function_calls'):
            llm_response.function_calls = llm_response.function_calls[:3]
        elif hasattr(llm_response, 'tool_calls'):
            llm_response.tool_calls = llm_response.tool_calls[:3]
           
    # Return None so the ADK proceeds to execute the tools
    print(f"{GREEN}[LLM LOG]{RESET} The model has successfully generated a response.")
    return None


### ----------- ###
### Agent Tools ###
# The ADK automatically parses this function and its docstring to create an AI tool.
def curl_web(url: str) -> str:
    """
    Fetches the text content of a given URL, acting like a curl command. 
    Useful for reading web pages or searching for answers online.
    
    Args:
        url (str): The full web address to fetch (e.g., 'https://example.com').
        
    Returns:
        str: The content of the web page, or an error message.
    """
    try:
        # We use a standard User-Agent so websites don't immediately block our request
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            # We truncate the response to 3000 characters to prevent blowing out your token limits!
            return response.read().decode('utf-8')[:3000]
    except Exception as e:
        return f"Failed to fetch {url}. Error: {str(e)}"


### --------------------------- ###
### Configure the model wrapper ###
# Notice the "openrouter/" prefix required for LiteLLM routing
openrouter_model = LiteLlm(
    model="openrouter/anthropic/claude-3-5-haiku",
    api_key=openrouter_api_key
)

# We can dynamically load instructions from a local markdown file
# with open("instructions.md", "r") as file:
#    agent_instructions = file.read()
agent_instructions = "You are a helpful AI assistant. Please provide short one sentence answers."


### -------------------------------------------------------- ###
### Define the Agent using the newly configured model object ### 
root_agent = Agent(
    name="openrouter_assistant",
    model=openrouter_model, 
    instruction=agent_instructions,

# Pass your new tool to the agent in a list
    tools=[curl_web],

# Attach custom functions to the corresponding callback parameters
    before_agent_callback=log_start_trigger,
    after_model_callback=log_model_finished_trigger,
    before_tool_callback=log_before_tool_trigger,
)

