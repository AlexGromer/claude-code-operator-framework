#!/usr/bin/env python3
"""
AutoGen Patterns Tool - Microsoft Multi-Agent Framework

Multi-agent conversation patterns from Microsoft AutoGen.
Addresses GAP-ORCH-004: Microsoft AutoGen patterns.
"""

import json
from typing import List, Dict, Any
from enum import Enum


class AgentType(Enum):
    """AutoGen agent types."""
    ASSISTANT = "assistant"
    USER_PROXY = "user_proxy"
    GROUP_CHAT = "group_chat"
    TEACHABLE = "teachable"


# Agent patterns
AGENT_PATTERNS: Dict[str, str] = {
    "basic_conversation": """
from autogen import AssistantAgent, UserProxyAgent

# Create assistant
assistant = AssistantAgent(
    name="assistant",
    llm_config={"model": "gpt-4", "api_key": "..."}
)

# Create user proxy (can execute code)
user_proxy = UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    code_execution_config={"work_dir": "coding"}
)

# Start conversation
user_proxy.initiate_chat(
    assistant,
    message="Write a Python function to calculate fibonacci numbers"
)
""",
    
    "group_chat": """
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

# Create specialized agents
coder = AssistantAgent(
    name="Coder",
    system_message="You are a Python developer.",
    llm_config=llm_config
)

reviewer = AssistantAgent(
    name="Reviewer",
    system_message="You review code for bugs and improvements.",
    llm_config=llm_config
)

tester = AssistantAgent(
    name="Tester",
    system_message="You write tests for code.",
    llm_config=llm_config
)

user_proxy = UserProxyAgent(
    name="User",
    human_input_mode="TERMINATE"
)

# Create group chat
groupchat = GroupChat(
    agents=[user_proxy, coder, reviewer, tester],
    messages=[],
    max_round=10
)

manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# Start group conversation
user_proxy.initiate_chat(
    manager,
    message="Create a function to sort a list and write tests for it"
)
""",
    
    "two_agent_coding": """
from autogen import AssistantAgent, UserProxyAgent

# Assistant that writes code
assistant = AssistantAgent(
    name="assistant",
    llm_config={
        "model": "gpt-4",
        "temperature": 0,
        "config_list": config_list
    },
    system_message="You are a helpful AI assistant that writes Python code."
)

# User proxy that executes code
user_proxy = UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={
        "work_dir": "workspace",
        "use_docker": False  # Set True for sandboxed execution
    }
)

# The conversation will auto-execute code
user_proxy.initiate_chat(
    assistant,
    message="Write and run a script that prints the first 10 prime numbers"
)
""",
    
    "teachable_agent": """
from autogen import AssistantAgent, UserProxyAgent
from autogen.agentchat.contrib.teachable_agent import TeachableAgent

# Agent that learns from interactions
teachable = TeachableAgent(
    name="teachable_agent",
    llm_config=llm_config,
    teach_config={
        "reset_db": False,  # Persist learnings
        "path_to_db_dir": "./teachable_db"
    }
)

user = UserProxyAgent(
    name="user",
    human_input_mode="ALWAYS"
)

# Teach the agent
user.initiate_chat(
    teachable,
    message="When I say 'deploy', always run 'kubectl apply -f deployment.yaml'"
)

# Agent remembers in future conversations
user.initiate_chat(teachable, message="deploy")
# Agent will use learned behavior
"""
}


# Configuration patterns
CONFIG_PATTERNS = {
    "llm_config": """
llm_config = {
    "config_list": [
        {
            "model": "gpt-4",
            "api_key": os.environ["OPENAI_API_KEY"]
        },
        {
            "model": "claude-sonnet-4-20250514",
            "api_key": os.environ["ANTHROPIC_API_KEY"],
            "api_type": "anthropic"
        }
    ],
    "temperature": 0,
    "timeout": 120,
    "cache_seed": 42  # For reproducibility
}
""",
    
    "code_execution": """
code_execution_config = {
    "work_dir": "workspace",
    "use_docker": True,  # Sandboxed execution
    "timeout": 60,
    "last_n_messages": 3  # Context for code execution
}

user_proxy = UserProxyAgent(
    name="executor",
    code_execution_config=code_execution_config
)
""",
    
    "function_calling": """
from autogen import register_function

# Define function
def get_weather(city: str) -> str:
    '''Get weather for a city.'''
    return f"Weather in {city}: 22°C, sunny"

# Register with agent
register_function(
    get_weather,
    caller=assistant,
    executor=user_proxy,
    description="Get current weather for a city"
)

# Agent can now call the function
user_proxy.initiate_chat(assistant, message="What's the weather in Paris?")
"""
}


# Integration patterns
INTEGRATION_PATTERNS = {
    "with_langchain": """
from autogen import AssistantAgent
from langchain.tools import Tool

# Wrap LangChain tool
langchain_tool = Tool(
    name="search",
    func=search_function,
    description="Search the web"
)

# Use in AutoGen agent
assistant = AssistantAgent(
    name="assistant",
    llm_config=llm_config,
    # Tools are registered separately
)
""",
    
    "with_rag": """
from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent

# RAG-enabled assistant
assistant = RetrieveAssistantAgent(
    name="assistant",
    llm_config=llm_config
)

# RAG-enabled user proxy
ragproxyagent = RetrieveUserProxyAgent(
    name="ragproxyagent",
    retrieve_config={
        "task": "qa",
        "docs_path": "./documents",
        "chunk_token_size": 2000,
        "model": "gpt-4"
    }
)

ragproxyagent.initiate_chat(
    assistant,
    problem="What does the documentation say about deployment?"
)
"""
}


def list_patterns() -> Dict[str, List[str]]:
    """List all available patterns."""
    return {
        "agents": list(AGENT_PATTERNS.keys()),
        "config": list(CONFIG_PATTERNS.keys()),
        "integration": list(INTEGRATION_PATTERNS.keys())
    }


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoGen Patterns")
    parser.add_argument("--list", action="store_true", help="List all patterns")
    parser.add_argument("--agent", type=str, help="Get agent pattern")
    parser.add_argument("--config", type=str, help="Get config pattern")
    parser.add_argument("--integration", type=str, help="Get integration pattern")
    
    args = parser.parse_args()
    
    if args.list:
        print(json.dumps(list_patterns(), indent=2))
    elif args.agent:
        if args.agent in AGENT_PATTERNS:
            print(AGENT_PATTERNS[args.agent])
        else:
            print(f"Agent pattern '{args.agent}' not found")
    elif args.config:
        if args.config in CONFIG_PATTERNS:
            print(CONFIG_PATTERNS[args.config])
        else:
            print(f"Config pattern '{args.config}' not found")
    elif args.integration:
        if args.integration in INTEGRATION_PATTERNS:
            print(INTEGRATION_PATTERNS[args.integration])
        else:
            print(f"Integration pattern '{args.integration}' not found")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
