#!/usr/bin/env python3
"""
Pydantic AI Tool - Type-Safe Agent Patterns

FastAPI-style type-safe agents with dependency injection.
Addresses GAP-ORCH-008: Pydantic AI type-safe agents.
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class AgentStyle(Enum):
    """Pydantic AI agent styles."""
    FUNCTION = "function"
    STRUCTURED = "structured"
    STREAMING = "streaming"
    CONVERSATIONAL = "conversational"


@dataclass
class AgentPattern:
    """Agent pattern definition."""
    name: str
    style: AgentStyle
    description: str
    code_example: str
    features: List[str]


# Agent patterns
AGENT_PATTERNS: Dict[str, AgentPattern] = {
    "basic_agent": AgentPattern(
        name="Basic Agent",
        style=AgentStyle.FUNCTION,
        description="Simple agent with type-safe responses",
        code_example="""
from pydantic_ai import Agent
from pydantic import BaseModel

class CityInfo(BaseModel):
    city: str
    country: str
    population: int

agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
    result_type=CityInfo,
    system_prompt="You provide city information."
)

result = agent.run_sync("Tell me about Tokyo")
print(result.data)  # CityInfo(city='Tokyo', country='Japan', population=...)
""",
        features=["Type-safe results", "Pydantic validation", "Simple API"]
    ),
    
    "with_tools": AgentPattern(
        name="Agent with Tools",
        style=AgentStyle.FUNCTION,
        description="Agent with custom tools",
        code_example="""
from pydantic_ai import Agent, RunContext

agent = Agent('anthropic:claude-sonnet-4-20250514')

@agent.tool
async def get_weather(ctx: RunContext[None], city: str) -> str:
    '''Get weather for a city.'''
    # Implementation
    return f"Weather in {city}: 22°C, sunny"

@agent.tool
async def search_database(ctx: RunContext[None], query: str) -> list[str]:
    '''Search the database.'''
    # Implementation
    return ["result1", "result2"]

result = await agent.run("What's the weather in Paris?")
""",
        features=["Custom tools", "Async support", "Tool docstrings"]
    ),
    
    "with_dependencies": AgentPattern(
        name="Agent with Dependencies",
        style=AgentStyle.STRUCTURED,
        description="Agent with FastAPI-style dependency injection",
        code_example="""
from pydantic_ai import Agent, RunContext
from dataclasses import dataclass

@dataclass
class DatabaseConn:
    host: str
    
    def query(self, sql: str) -> list:
        return []

@dataclass
class Dependencies:
    db: DatabaseConn
    user_id: int

agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
    deps_type=Dependencies
)

@agent.tool
async def get_user_orders(ctx: RunContext[Dependencies]) -> list:
    '''Get user orders from database.'''
    return ctx.deps.db.query(f"SELECT * FROM orders WHERE user_id = {ctx.deps.user_id}")

# Run with dependencies
deps = Dependencies(db=DatabaseConn("localhost"), user_id=123)
result = await agent.run("Show my recent orders", deps=deps)
""",
        features=["Dependency injection", "Type-safe deps", "Testable"]
    ),
    
    "streaming": AgentPattern(
        name="Streaming Agent",
        style=AgentStyle.STREAMING,
        description="Agent with streaming responses",
        code_example="""
from pydantic_ai import Agent

agent = Agent('anthropic:claude-sonnet-4-20250514')

async def stream_response():
    async with agent.run_stream("Write a story") as response:
        async for chunk in response.stream_text():
            print(chunk, end="", flush=True)
        
        # Get structured result after streaming
        result = await response.get_data()
        return result

import asyncio
asyncio.run(stream_response())
""",
        features=["Text streaming", "Structured final result", "Async context"]
    ),
    
    "conversation": AgentPattern(
        name="Conversational Agent",
        style=AgentStyle.CONVERSATIONAL,
        description="Agent with conversation history",
        code_example="""
from pydantic_ai import Agent

agent = Agent('anthropic:claude-sonnet-4-20250514')

# First turn
result1 = await agent.run("My name is Alice")

# Continue conversation with history
result2 = await agent.run(
    "What's my name?",
    message_history=result1.all_messages()
)

print(result2.data)  # "Your name is Alice"
""",
        features=["Message history", "Multi-turn", "Context preservation"]
    )
}


# Model configuration patterns
MODEL_PATTERNS = {
    "anthropic": """
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel

model = AnthropicModel('claude-sonnet-4-20250514')
agent = Agent(model, system_prompt="...")

# Or use string shortcut
agent = Agent('anthropic:claude-sonnet-4-20250514')
""",
    
    "openai": """
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

model = OpenAIModel('gpt-4o')
agent = Agent(model)

# Or string shortcut
agent = Agent('openai:gpt-4o')
""",
    
    "ollama": """
from pydantic_ai import Agent
from pydantic_ai.models.ollama import OllamaModel

model = OllamaModel('llama3')
agent = Agent(model)

# Or string shortcut
agent = Agent('ollama:llama3')
""",
    
    "custom_settings": """
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

settings = ModelSettings(
    temperature=0.7,
    max_tokens=2000,
    timeout=30.0
)

agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
    model_settings=settings
)
"""
}


# Testing patterns
TESTING_PATTERNS = {
    "mock_model": """
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

# Create test model that returns predefined responses
test_model = TestModel()

@test_model.call_handler
def handle_call(messages):
    return "Mocked response"

agent = Agent(test_model)
result = agent.run_sync("test")
assert result.data == "Mocked response"
""",
    
    "function_model": """
from pydantic_ai import Agent
from pydantic_ai.models.function import FunctionModel

# Model that calls a function for responses
def my_function(messages: list) -> str:
    return "Function response"

agent = Agent(FunctionModel(my_function))
""",
    
    "snapshot_testing": """
import pytest
from pydantic_ai import Agent

@pytest.fixture
def agent():
    return Agent('anthropic:claude-sonnet-4-20250514')

def test_agent_response(agent, snapshot):
    result = agent.run_sync("What is 2+2?")
    assert result.data == snapshot
"""
}


def get_agent_pattern(name: str) -> Optional[Dict[str, Any]]:
    """Get a specific agent pattern."""
    if name in AGENT_PATTERNS:
        p = AGENT_PATTERNS[name]
        return {
            "name": p.name,
            "style": p.style.value,
            "description": p.description,
            "code": p.code_example,
            "features": p.features
        }
    return None


def list_patterns() -> Dict[str, List[str]]:
    """List all available patterns."""
    return {
        "agents": list(AGENT_PATTERNS.keys()),
        "models": list(MODEL_PATTERNS.keys()),
        "testing": list(TESTING_PATTERNS.keys())
    }


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pydantic AI Patterns")
    parser.add_argument("--list", action="store_true", help="List all patterns")
    parser.add_argument("--agent", type=str, help="Get agent pattern")
    parser.add_argument("--model", type=str, help="Get model config")
    parser.add_argument("--testing", type=str, help="Get testing pattern")
    
    args = parser.parse_args()
    
    if args.list:
        print(json.dumps(list_patterns(), indent=2))
    
    elif args.agent:
        pattern = get_agent_pattern(args.agent)
        if pattern:
            print(json.dumps(pattern, indent=2))
            print("\n--- Code Example ---")
            print(pattern["code"])
        else:
            print(f"Pattern '{args.agent}' not found")
    
    elif args.model:
        if args.model in MODEL_PATTERNS:
            print(MODEL_PATTERNS[args.model])
        else:
            print(f"Model pattern '{args.model}' not found")
    
    elif args.testing:
        if args.testing in TESTING_PATTERNS:
            print(TESTING_PATTERNS[args.testing])
        else:
            print(f"Testing pattern '{args.testing}' not found")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
