#!/usr/bin/env python3
"""
LangChain Agent Template (GAP-ORCH-001)

Template for building LangChain-based agents with Claude.
Includes tool integration, memory, and safety patterns.

Usage:
    1. Copy this template to your project
    2. Configure API keys and tools
    3. Customize for your use case

Requirements:
    pip install langchain langchain-anthropic langchain-community
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

# LangChain imports
try:
    from langchain_anthropic import ChatAnthropic
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain.tools import Tool, StructuredTool
    from langchain.memory import ConversationBufferWindowMemory
    from langchain_core.messages import HumanMessage, AIMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("LangChain not installed. Install with: pip install langchain langchain-anthropic")


# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG = {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.7,
    "max_tokens": 4096,
    "memory_window": 10,  # Keep last 10 exchanges
}

# =============================================================================
# SAFETY PATTERNS
# =============================================================================

SAFETY_PROMPT = """
## Safety Guidelines

You are a helpful AI assistant. Follow these safety guidelines:

1. Never execute destructive operations without explicit user confirmation
2. Refuse requests that could harm users or systems
3. Maintain user privacy - don't store or leak sensitive data
4. Be transparent about your capabilities and limitations
5. If unsure, ask for clarification rather than guessing

## Authorization Levels
- READ: Can view files and data (autonomous)
- ANALYZE: Can process and analyze data (autonomous)
- MODIFY: Requires user confirmation
- DESTRUCTIVE: Requires explicit approval with confirmation phrase
"""


# =============================================================================
# CUSTOM TOOLS
# =============================================================================

def create_file_reader_tool():
    """Create a safe file reading tool."""

    def read_file(file_path: str) -> str:
        """Read contents of a file safely."""
        import os

        # Safety checks
        forbidden_paths = ['/etc/shadow', '/etc/passwd', '~/.ssh/', '.env']
        for forbidden in forbidden_paths:
            if forbidden in file_path:
                return f"Error: Access to {file_path} is not permitted"

        # Path traversal check
        if '..' in file_path:
            return "Error: Path traversal not allowed"

        try:
            with open(os.path.expanduser(file_path), 'r') as f:
                content = f.read()
                # Truncate if too large
                if len(content) > 10000:
                    return content[:10000] + "\n... [truncated]"
                return content
        except FileNotFoundError:
            return f"Error: File not found: {file_path}"
        except PermissionError:
            return f"Error: Permission denied: {file_path}"
        except Exception as e:
            return f"Error reading file: {str(e)}"

    return Tool(
        name="read_file",
        description="Read the contents of a file. Input should be the file path.",
        func=read_file,
    )


def create_calculator_tool():
    """Create a safe calculator tool."""

    def calculate(expression: str) -> str:
        """Evaluate a mathematical expression safely."""
        import re

        # Only allow safe characters
        if not re.match(r'^[\d\s\+\-\*\/\(\)\.\%\^]+$', expression):
            return "Error: Invalid characters in expression"

        # Replace ^ with ** for Python
        expression = expression.replace('^', '**')

        try:
            # Use eval with restricted globals
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Error: {str(e)}"

    return Tool(
        name="calculator",
        description="Evaluate mathematical expressions. Input should be a math expression like '2 + 2' or '(10 * 5) / 2'.",
        func=calculate,
    )


def create_web_search_tool():
    """Create a mock web search tool."""

    def web_search(query: str) -> str:
        """Search the web for information."""
        # In production, integrate with actual search API
        return f"[Mock search results for: {query}]\n\nSearch functionality requires API integration."

    return Tool(
        name="web_search",
        description="Search the web for information. Input should be a search query.",
        func=web_search,
    )


# =============================================================================
# AGENT CREATION
# =============================================================================

def create_claude_agent(
    tools: Optional[List] = None,
    system_prompt: str = None,
    memory: bool = True,
) -> Optional[AgentExecutor]:
    """
    Create a LangChain agent with Claude.

    Args:
        tools: List of tools for the agent
        system_prompt: Custom system prompt
        memory: Whether to enable conversation memory

    Returns:
        AgentExecutor or None if LangChain not available
    """
    if not LANGCHAIN_AVAILABLE:
        print("Error: LangChain not available")
        return None

    # Initialize Claude
    llm = ChatAnthropic(
        model=CONFIG["model"],
        temperature=CONFIG["temperature"],
        max_tokens=CONFIG["max_tokens"],
    )

    # Default tools if none provided
    if tools is None:
        tools = [
            create_file_reader_tool(),
            create_calculator_tool(),
            create_web_search_tool(),
        ]

    # Build prompt
    default_system = SAFETY_PROMPT + "\n\nYou are a helpful AI assistant."
    system = system_prompt or default_system

    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # Create agent
    agent = create_tool_calling_agent(llm, tools, prompt)

    # Configure memory
    memory_instance = None
    if memory:
        memory_instance = ConversationBufferWindowMemory(
            k=CONFIG["memory_window"],
            memory_key="chat_history",
            return_messages=True,
        )

    # Create executor
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory_instance,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10,
    )

    return executor


# =============================================================================
# CONVERSATION WRAPPER
# =============================================================================

class ClaudeAgent:
    """
    High-level wrapper for Claude agent.

    Example:
        agent = ClaudeAgent()
        response = agent.chat("What is 2 + 2?")
        print(response)
    """

    def __init__(
        self,
        tools: Optional[List] = None,
        system_prompt: str = None,
    ):
        self.executor = create_claude_agent(tools, system_prompt)
        self.history = []

    def chat(self, message: str) -> str:
        """Send a message and get a response."""
        if not self.executor:
            return "Error: Agent not initialized"

        try:
            result = self.executor.invoke({"input": message})
            response = result.get("output", "No response")

            self.history.append({
                "timestamp": datetime.now().isoformat(),
                "input": message,
                "output": response,
            })

            return response
        except Exception as e:
            return f"Error: {str(e)}"

    def clear_history(self):
        """Clear conversation history."""
        self.history = []
        if self.executor and self.executor.memory:
            self.executor.memory.clear()


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

def example_usage():
    """Demonstrate agent usage."""
    print("=" * 60)
    print("LangChain Claude Agent Template")
    print("=" * 60)

    if not LANGCHAIN_AVAILABLE:
        print("\nLangChain not installed. This is a template file.")
        print("Install with: pip install langchain langchain-anthropic")
        return

    # Create agent
    agent = ClaudeAgent()

    # Example interactions
    examples = [
        "What is 15 * 23?",
        "Read the file README.md",
        "Search for Python best practices",
    ]

    for query in examples:
        print(f"\n> {query}")
        response = agent.chat(query)
        print(f"< {response}")


if __name__ == "__main__":
    example_usage()
