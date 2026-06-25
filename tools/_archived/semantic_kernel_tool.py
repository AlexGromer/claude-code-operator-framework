#!/usr/bin/env python3
"""
Microsoft Semantic Kernel Tool (GAP-ORCH-013)

Provides patterns and utilities for Microsoft Semantic Kernel -
an SDK for integrating LLMs with conventional programming languages.

Key Features:
- Kernel configuration patterns
- Plugin and function templates
- Memory and RAG integration
- Planner patterns
- Multi-model orchestration

Usage:
    python semantic_kernel_tool.py --pattern basic_kernel --show
    python semantic_kernel_tool.py --list
    python semantic_kernel_tool.py --generate-plugin "Calculator"
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class PatternCategory(Enum):
    """Categories of Semantic Kernel patterns."""
    KERNEL = "kernel"
    PLUGIN = "plugin"
    MEMORY = "memory"
    PLANNER = "planner"
    CONNECTOR = "connector"
    AGENT = "agent"


@dataclass
class SKPattern:
    """Represents a Semantic Kernel pattern."""
    name: str
    category: PatternCategory
    description: str
    python_code: str
    csharp_code: Optional[str] = None
    use_cases: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


# Semantic Kernel patterns
SK_PATTERNS: Dict[str, SKPattern] = {
    "basic_kernel": SKPattern(
        name="Basic Kernel Setup",
        category=PatternCategory.KERNEL,
        description="Initialize Semantic Kernel with OpenAI or Azure OpenAI",
        python_code='''
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    AzureChatCompletion
)

# Create kernel
kernel = sk.Kernel()

# Option 1: OpenAI
kernel.add_service(
    OpenAIChatCompletion(
        service_id="openai",
        ai_model_id="gpt-4",
        api_key="your-api-key"
    )
)

# Option 2: Azure OpenAI
kernel.add_service(
    AzureChatCompletion(
        service_id="azure",
        deployment_name="gpt-4",
        endpoint="https://your-resource.openai.azure.com/",
        api_key="your-api-key"
    )
)

# Simple invocation
result = await kernel.invoke_prompt("What is the capital of France?")
print(result)
''',
        use_cases=[
            "Getting started with SK",
            "Basic LLM invocation",
            "Multi-provider setup"
        ],
        dependencies=["semantic-kernel", "openai"]
    ),

    "native_plugin": SKPattern(
        name="Native Function Plugin",
        category=PatternCategory.PLUGIN,
        description="Create plugins with Python functions",
        python_code='''
import semantic_kernel as sk
from semantic_kernel.functions import kernel_function

class MathPlugin:
    """A plugin with math operations."""

    @kernel_function(
        name="add",
        description="Adds two numbers together"
    )
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b

    @kernel_function(
        name="multiply",
        description="Multiplies two numbers"
    )
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b

    @kernel_function(
        name="divide",
        description="Divides first number by second"
    )
    def divide(self, a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

# Register plugin
kernel = sk.Kernel()
kernel.add_plugin(MathPlugin(), plugin_name="Math")

# Use the plugin
result = await kernel.invoke(
    kernel.plugins["Math"]["add"],
    a=5,
    b=3
)
print(f"5 + 3 = {result}")  # Output: 8
''',
        use_cases=[
            "Custom tool creation",
            "Business logic integration",
            "Extending LLM capabilities"
        ],
        dependencies=["semantic-kernel"]
    ),

    "semantic_plugin": SKPattern(
        name="Semantic Function Plugin",
        category=PatternCategory.PLUGIN,
        description="Create plugins with prompt templates",
        python_code='''
import semantic_kernel as sk
from semantic_kernel.prompt_template import PromptTemplateConfig

# Define prompt template
prompt_template = """
You are a professional summarizer.
Summarize the following text in {{$style}} style:

{{$input}}

Summary:
"""

# Create kernel and add service
kernel = sk.Kernel()
kernel.add_service(OpenAIChatCompletion(
    service_id="default",
    ai_model_id="gpt-4",
    api_key="your-key"
))

# Create semantic function
summarize = kernel.add_function(
    plugin_name="TextPlugin",
    function_name="Summarize",
    prompt=prompt_template,
    prompt_template_config=PromptTemplateConfig(
        template_format="semantic-kernel",
        input_variables=[
            {"name": "input", "description": "Text to summarize"},
            {"name": "style", "description": "Style of summary", "default": "concise"}
        ]
    )
)

# Use the function
result = await kernel.invoke(
    summarize,
    input="Long text here...",
    style="bullet points"
)
print(result)
''',
        use_cases=[
            "Prompt engineering",
            "Reusable prompts",
            "Template-based generation"
        ],
        dependencies=["semantic-kernel"]
    ),

    "memory_store": SKPattern(
        name="Memory and RAG",
        category=PatternCategory.MEMORY,
        description="Semantic memory with vector store for RAG",
        python_code='''
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAITextEmbedding
from semantic_kernel.memory import SemanticTextMemory, VolatileMemoryStore

# Create kernel
kernel = sk.Kernel()

# Add embedding service
embedding = OpenAITextEmbedding(
    ai_model_id="text-embedding-ada-002",
    api_key="your-key"
)
kernel.add_service(embedding)

# Create memory store (use ChromaDB, Pinecone, etc. in production)
memory_store = VolatileMemoryStore()
memory = SemanticTextMemory(
    storage=memory_store,
    embeddings_generator=embedding
)

# Save memories
await memory.save_information(
    collection="docs",
    id="doc1",
    text="Semantic Kernel is an SDK for AI orchestration."
)
await memory.save_information(
    collection="docs",
    id="doc2",
    text="It supports Python, C#, and Java."
)

# Search memories (RAG retrieval)
results = await memory.search(
    collection="docs",
    query="What languages does SK support?",
    limit=2
)

for result in results:
    print(f"Relevance: {result.relevance:.2f}")
    print(f"Text: {result.text}")
''',
        use_cases=[
            "Document Q&A",
            "Knowledge base integration",
            "Contextual retrieval"
        ],
        dependencies=["semantic-kernel", "chromadb"]
    ),

    "handlebars_planner": SKPattern(
        name="Handlebars Planner",
        category=PatternCategory.PLANNER,
        description="Auto-generate execution plans from goals",
        python_code='''
import semantic_kernel as sk
from semantic_kernel.planners import HandlebarsPlanner

# Create kernel with plugins
kernel = sk.Kernel()
kernel.add_service(OpenAIChatCompletion(...))

# Add plugins
kernel.add_plugin(MathPlugin(), "Math")
kernel.add_plugin(TimePlugin(), "Time")
kernel.add_plugin(TextPlugin(), "Text")

# Create planner
planner = HandlebarsPlanner(kernel)

# Generate plan from goal
goal = "Calculate how many hours until midnight and multiply by 60 to get minutes"
plan = await planner.create_plan(goal)

print(f"Generated plan:\n{plan}")

# Execute plan
result = await plan.invoke(kernel)
print(f"Result: {result}")
''',
        use_cases=[
            "Goal-based execution",
            "Multi-step tasks",
            "Dynamic tool selection"
        ],
        dependencies=["semantic-kernel"]
    ),

    "function_calling_planner": SKPattern(
        name="Function Calling Planner",
        category=PatternCategory.PLANNER,
        description="Use OpenAI function calling for planning",
        python_code='''
import semantic_kernel as sk
from semantic_kernel.planners.function_calling_stepwise_planner import (
    FunctionCallingStepwisePlanner,
    FunctionCallingStepwisePlannerOptions
)

# Create kernel with plugins
kernel = sk.Kernel()
kernel.add_service(OpenAIChatCompletion(
    service_id="default",
    ai_model_id="gpt-4",
    api_key="your-key"
))

# Add plugins
kernel.add_plugin(WebSearchPlugin(), "Search")
kernel.add_plugin(MathPlugin(), "Math")

# Configure planner
options = FunctionCallingStepwisePlannerOptions(
    max_iterations=10,
    max_tokens=4000
)

planner = FunctionCallingStepwisePlanner(
    kernel=kernel,
    options=options
)

# Execute with goal
goal = "Find the current population of Tokyo and calculate what 1% of it is"
result = await planner.invoke(goal)

print(f"Final result: {result.final_answer}")
print(f"Steps taken: {len(result.chat_history)}")
''',
        use_cases=[
            "Complex reasoning",
            "Multi-tool orchestration",
            "Iterative problem solving"
        ],
        dependencies=["semantic-kernel"]
    ),

    "chat_completion": SKPattern(
        name="Chat Completion",
        category=PatternCategory.CONNECTOR,
        description="Conversational chat with history",
        python_code='''
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.contents import ChatHistory

# Create kernel
kernel = sk.Kernel()
kernel.add_service(OpenAIChatCompletion(
    service_id="chat",
    ai_model_id="gpt-4",
    api_key="your-key"
))

# Create chat history
history = ChatHistory()
history.add_system_message("You are a helpful assistant.")

# Chat loop
async def chat(user_input: str) -> str:
    history.add_user_message(user_input)

    result = await kernel.invoke_prompt(
        prompt="{{$history}}",
        history=history
    )

    assistant_message = str(result)
    history.add_assistant_message(assistant_message)

    return assistant_message

# Example conversation
response1 = await chat("Hello!")
response2 = await chat("What's 2 + 2?")
response3 = await chat("And if I add 3 more?")  # Has context from previous
''',
        use_cases=[
            "Chatbots",
            "Conversational AI",
            "Context-aware responses"
        ],
        dependencies=["semantic-kernel"]
    ),

    "streaming": SKPattern(
        name="Streaming Responses",
        category=PatternCategory.CONNECTOR,
        description="Stream LLM responses token by token",
        python_code='''
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

# Create kernel
kernel = sk.Kernel()
kernel.add_service(OpenAIChatCompletion(
    service_id="chat",
    ai_model_id="gpt-4",
    api_key="your-key"
))

# Stream response
async def stream_response(prompt: str):
    async for chunk in kernel.invoke_stream(
        kernel.plugins["TextPlugin"]["Generate"],
        prompt=prompt
    ):
        print(chunk, end="", flush=True)
    print()  # Newline at end

# Usage
await stream_response("Write a haiku about programming")
''',
        use_cases=[
            "Real-time UI updates",
            "Long-form generation",
            "Progressive display"
        ],
        dependencies=["semantic-kernel"]
    ),

    "filters": SKPattern(
        name="Filters and Hooks",
        category=PatternCategory.KERNEL,
        description="Add pre/post processing filters",
        python_code='''
import semantic_kernel as sk
from semantic_kernel.filters import (
    FunctionInvocationContext,
    PromptRenderContext
)

# Create kernel
kernel = sk.Kernel()

# Pre-invocation filter (before function runs)
@kernel.filter("function_invocation")
async def pre_invocation_filter(
    context: FunctionInvocationContext,
    next_filter
):
    print(f"Calling function: {context.function.name}")
    print(f"Arguments: {context.arguments}")

    # Continue to next filter/function
    await next_filter(context)

    print(f"Result: {context.result}")

# Prompt render filter (modify prompts)
@kernel.filter("prompt_render")
async def prompt_filter(
    context: PromptRenderContext,
    next_filter
):
    # Add safety prefix to all prompts
    context.rendered_prompt = (
        "Remember to be helpful and harmless.\\n" +
        context.rendered_prompt
    )
    await next_filter(context)

# Exception filter
@kernel.filter("function_invocation")
async def exception_filter(context, next_filter):
    try:
        await next_filter(context)
    except Exception as e:
        print(f"Error in {context.function.name}: {e}")
        # Handle gracefully
        context.result = "An error occurred"
''',
        use_cases=[
            "Logging and monitoring",
            "Safety guardrails",
            "Error handling"
        ],
        dependencies=["semantic-kernel"]
    ),

    "agent_pattern": SKPattern(
        name="Agent with Plugins",
        category=PatternCategory.AGENT,
        description="Create an agent that uses plugins autonomously",
        python_code='''
import semantic_kernel as sk
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

# Create kernel with plugins
kernel = sk.Kernel()
kernel.add_service(OpenAIChatCompletion(
    service_id="agent",
    ai_model_id="gpt-4",
    api_key="your-key"
))

# Add plugins for agent to use
kernel.add_plugin(FilePlugin(), "Files")
kernel.add_plugin(WebSearchPlugin(), "Search")
kernel.add_plugin(CodeExecutionPlugin(), "Code")

# Create agent
agent = ChatCompletionAgent(
    kernel=kernel,
    service_id="agent",
    name="ResearchAgent",
    instructions="""
    You are a research agent. You can:
    - Search the web for information
    - Read and write files
    - Execute code for analysis

    Complete tasks step by step, using tools as needed.
    """
)

# Run agent
async def run_agent(task: str):
    response = await agent.invoke(task)
    return response

result = await run_agent(
    "Research the latest Python 3.12 features and save a summary to features.md"
)
''',
        use_cases=[
            "Autonomous task execution",
            "Research assistants",
            "Code automation"
        ],
        dependencies=["semantic-kernel"]
    ),

    "multi_agent": SKPattern(
        name="Multi-Agent Collaboration",
        category=PatternCategory.AGENT,
        description="Multiple agents working together",
        python_code='''
import semantic_kernel as sk
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent

# Create kernel
kernel = sk.Kernel()
kernel.add_service(OpenAIChatCompletion(...))

# Define specialized agents
researcher = ChatCompletionAgent(
    kernel=kernel,
    name="Researcher",
    instructions="You research topics and provide factual information."
)

critic = ChatCompletionAgent(
    kernel=kernel,
    name="Critic",
    instructions="You review information for accuracy and completeness."
)

writer = ChatCompletionAgent(
    kernel=kernel,
    name="Writer",
    instructions="You write clear, engaging content based on research."
)

# Create group chat
group_chat = AgentGroupChat(
    agents=[researcher, critic, writer],
    termination_condition=lambda history: (
        len(history) >= 10 or
        "FINAL DRAFT" in str(history[-1])
    )
)

# Run collaborative task
async def collaborative_writing(topic: str):
    async for message in group_chat.invoke(
        f"Create a blog post about: {topic}"
    ):
        print(f"[{message.agent_name}]: {message.content}")

await collaborative_writing("The future of AI")
''',
        use_cases=[
            "Content creation pipelines",
            "Review workflows",
            "Complex problem solving"
        ],
        dependencies=["semantic-kernel"]
    ),
}


@dataclass
class PluginTemplate:
    """Template for generating new plugins."""
    name: str
    functions: List[Dict[str, str]]
    description: str


def generate_plugin_code(name: str, functions: List[Dict[str, str]]) -> str:
    """Generate plugin code from template."""
    func_code = []
    for func in functions:
        func_code.append(f'''
    @kernel_function(
        name="{func.get('name', 'function')}",
        description="{func.get('description', 'A function')}"
    )
    def {func.get('name', 'function')}(self{', ' + func.get('params', '') if func.get('params') else ''}) -> {func.get('return_type', 'str')}:
        """
        {func.get('description', 'A function')}
        """
        # TODO: Implement
        pass
''')

    return f'''import semantic_kernel as sk
from semantic_kernel.functions import kernel_function


class {name}Plugin:
    """
    {name} plugin for Semantic Kernel.
    """
{"".join(func_code)}

# Register with kernel
# kernel.add_plugin({name}Plugin(), plugin_name="{name}")
'''


def list_patterns(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all available patterns."""
    patterns = []
    for name, pattern in SK_PATTERNS.items():
        if category and pattern.category.value != category:
            continue
        patterns.append({
            "name": name,
            "display_name": pattern.name,
            "category": pattern.category.value,
            "description": pattern.description,
            "use_cases": pattern.use_cases,
            "dependencies": pattern.dependencies
        })
    return patterns


def get_pattern(name: str) -> Optional[SKPattern]:
    """Get a specific pattern by name."""
    return SK_PATTERNS.get(name)


def show_pattern(name: str) -> str:
    """Display a pattern with full details."""
    pattern = get_pattern(name)
    if not pattern:
        return f"Pattern '{name}' not found"

    output = [
        f"# {pattern.name}",
        f"Category: {pattern.category.value}",
        f"Description: {pattern.description}",
        "",
        "## Python Code",
        "```python",
        pattern.python_code.strip(),
        "```",
    ]

    if pattern.csharp_code:
        output.extend([
            "",
            "## C# Code",
            "```csharp",
            pattern.csharp_code.strip(),
            "```"
        ])

    output.extend([
        "",
        "## Use Cases",
        *[f"- {uc}" for uc in pattern.use_cases],
        "",
        "## Dependencies",
        *[f"- {dep}" for dep in pattern.dependencies]
    ])

    return "\n".join(output)


def get_statistics() -> Dict[str, Any]:
    """Get statistics about available patterns."""
    stats = {
        "total_patterns": len(SK_PATTERNS),
        "by_category": {},
        "total_use_cases": 0,
        "unique_dependencies": set()
    }

    for pattern in SK_PATTERNS.values():
        cat = pattern.category.value
        stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
        stats["total_use_cases"] += len(pattern.use_cases)
        stats["unique_dependencies"].update(pattern.dependencies)

    stats["unique_dependencies"] = list(stats["unique_dependencies"])
    return stats


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Microsoft Semantic Kernel Tool"
    )
    parser.add_argument("--list", action="store_true", help="List all patterns")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--pattern", help="Show specific pattern")
    parser.add_argument("--show", action="store_true", help="Show pattern details")
    parser.add_argument("--generate-plugin", metavar="NAME",
                       help="Generate plugin template")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.list:
        patterns = list_patterns(args.category)
        if args.json:
            print(json.dumps(patterns, indent=2))
        else:
            print(f"\n{'='*60}")
            print("MICROSOFT SEMANTIC KERNEL PATTERNS")
            print(f"{'='*60}\n")
            for p in patterns:
                print(f"  {p['name']:<25} [{p['category']}]")
                print(f"    {p['description']}")
                print()

    elif args.pattern:
        if args.show:
            print(show_pattern(args.pattern))
        else:
            pattern = get_pattern(args.pattern)
            if pattern:
                if args.json:
                    print(json.dumps({
                        "name": pattern.name,
                        "category": pattern.category.value,
                        "description": pattern.description,
                        "python_code": pattern.python_code,
                        "use_cases": pattern.use_cases,
                        "dependencies": pattern.dependencies
                    }, indent=2))
                else:
                    print(pattern.python_code)
            else:
                print(f"Pattern '{args.pattern}' not found")
                sys.exit(1)

    elif args.generate_plugin:
        # Generate basic plugin template
        plugin_code = generate_plugin_code(
            args.generate_plugin,
            [
                {"name": "process", "description": "Process input data",
                 "params": "input_data: str", "return_type": "str"},
                {"name": "validate", "description": "Validate data",
                 "params": "data: str", "return_type": "bool"}
            ]
        )
        print(plugin_code)

    elif args.stats:
        stats = get_statistics()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"\n{'='*40}")
            print("SEMANTIC KERNEL PATTERNS STATISTICS")
            print(f"{'='*40}")
            print(f"Total patterns: {stats['total_patterns']}")
            print(f"Total use cases: {stats['total_use_cases']}")
            print("\nBy category:")
            for cat, count in stats['by_category'].items():
                print(f"  {cat}: {count}")
            print("\nDependencies:")
            for dep in stats['unique_dependencies']:
                print(f"  - {dep}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
