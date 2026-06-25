#!/usr/bin/env python3
"""
LangChain Patterns Tool

Production patterns and best practices for LangChain.
Addresses GAP-ORCH-001: LangChain detailed coverage.
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class ChainType(Enum):
    """LangChain chain types."""
    LLM = "llm"
    SEQUENTIAL = "sequential"
    ROUTER = "router"
    MAP_REDUCE = "map_reduce"
    STUFF = "stuff"
    REFINE = "refine"


class AgentType(Enum):
    """LangChain agent types."""
    ZERO_SHOT = "zero-shot-react-description"
    CONVERSATIONAL = "conversational-react-description"
    OPENAI_FUNCTIONS = "openai-functions"
    STRUCTURED = "structured-chat-zero-shot-react-description"


@dataclass
class ChainPattern:
    """Chain pattern definition."""
    name: str
    type: ChainType
    description: str
    code_example: str
    use_cases: List[str]


@dataclass
class AgentPattern:
    """Agent pattern definition."""
    name: str
    type: AgentType
    description: str
    tools_required: List[str]
    code_example: str


# Production chain patterns
CHAIN_PATTERNS: Dict[str, ChainPattern] = {
    "simple_qa": ChainPattern(
        name="Simple QA Chain",
        type=ChainType.LLM,
        description="Basic question-answering with context",
        code_example="""
from langchain_anthropic import ChatAnthropic
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

llm = ChatAnthropic(model="claude-sonnet-4-20250514")
prompt = PromptTemplate(
    input_variables=["question", "context"],
    template="Context: {context}\\n\\nQuestion: {question}\\n\\nAnswer:"
)
chain = LLMChain(llm=llm, prompt=prompt)
result = chain.invoke({"question": "...", "context": "..."})
""",
        use_cases=["FAQ systems", "Document QA", "Support bots"]
    ),
    
    "sequential": ChainPattern(
        name="Sequential Chain",
        type=ChainType.SEQUENTIAL,
        description="Multiple chains executed in sequence",
        code_example="""
from langchain.chains import SequentialChain

chain = SequentialChain(
    chains=[research_chain, analysis_chain, summary_chain],
    input_variables=["topic"],
    output_variables=["summary"]
)
result = chain.invoke({"topic": "AI safety"})
""",
        use_cases=["Multi-step reasoning", "Report generation", "Analysis pipelines"]
    ),
    
    "rag_chain": ChainPattern(
        name="RAG Chain",
        type=ChainType.STUFF,
        description="Retrieval-Augmented Generation pattern",
        code_example="""
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Chroma
from langchain_anthropic import ChatAnthropic

vectorstore = Chroma.from_documents(docs, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

qa_chain = RetrievalQA.from_chain_type(
    llm=ChatAnthropic(model="claude-sonnet-4-20250514"),
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True
)
result = qa_chain.invoke({"query": "..."})
""",
        use_cases=["Knowledge bases", "Document search", "Enterprise QA"]
    ),
    
    "router": ChainPattern(
        name="Router Chain",
        type=ChainType.ROUTER,
        description="Route to specialized chains based on input",
        code_example="""
from langchain.chains.router import MultiPromptChain
from langchain.chains.router.llm_router import LLMRouterChain

prompt_infos = [
    {"name": "physics", "description": "...", "prompt_template": physics_template},
    {"name": "math", "description": "...", "prompt_template": math_template},
]

chain = MultiPromptChain.from_prompts(
    llm=llm,
    prompt_infos=prompt_infos,
    default_chain=default_chain
)
""",
        use_cases=["Multi-domain assistants", "Specialized routing", "Expert systems"]
    )
}


# Agent patterns
AGENT_PATTERNS: Dict[str, AgentPattern] = {
    "react_agent": AgentPattern(
        name="ReAct Agent",
        type=AgentType.ZERO_SHOT,
        description="Reasoning and Acting agent pattern",
        tools_required=["search", "calculator"],
        code_example="""
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub

prompt = hub.pull("hwchase17/react")
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
result = agent_executor.invoke({"input": "..."})
"""
    ),
    
    "openai_functions": AgentPattern(
        name="OpenAI Functions Agent",
        type=AgentType.OPENAI_FUNCTIONS,
        description="Function-calling based agent (works with Claude)",
        tools_required=["any"],
        code_example="""
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain import hub

prompt = hub.pull("hwchase17/openai-functions-agent")
agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)
"""
    ),
    
    "conversational": AgentPattern(
        name="Conversational Agent",
        type=AgentType.CONVERSATIONAL,
        description="Agent with conversation memory",
        tools_required=["search"],
        code_example="""
from langchain.agents import create_react_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
agent_executor = AgentExecutor(
    agent=agent, tools=tools, memory=memory, verbose=True
)
"""
    )
}


# LCEL (LangChain Expression Language) patterns
LCEL_PATTERNS = {
    "basic_chain": """
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_template("Tell me about {topic}")
model = ChatAnthropic(model="claude-sonnet-4-20250514")
parser = StrOutputParser()

chain = prompt | model | parser
result = chain.invoke({"topic": "AI"})
""",
    
    "parallel_chain": """
from langchain_core.runnables import RunnableParallel

analysis = RunnableParallel(
    summary=summary_chain,
    sentiment=sentiment_chain,
    keywords=keyword_chain
)
result = analysis.invoke({"text": document})
""",
    
    "fallback_chain": """
from langchain_core.runnables import RunnableWithFallbacks

chain_with_fallback = main_chain.with_fallbacks([backup_chain])
result = chain_with_fallback.invoke(input_data)
""",
    
    "streaming": """
async for chunk in chain.astream({"topic": "AI"}):
    print(chunk, end="", flush=True)
"""
}


# Production best practices
BEST_PRACTICES = {
    "caching": """
# Enable caching for repeated queries
from langchain.globals import set_llm_cache
from langchain.cache import SQLiteCache
set_llm_cache(SQLiteCache(database_path=".langchain.db"))
""",
    
    "rate_limiting": """
# Add rate limiting
from langchain.callbacks import get_openai_callback
with get_openai_callback() as cb:
    result = chain.invoke(input)
    print(f"Tokens used: {cb.total_tokens}")
""",
    
    "error_handling": """
# Robust error handling
from langchain_core.runnables import RunnableConfig

config = RunnableConfig(
    max_retries=3,
    retry_on_exception=True,
    tags=["production"]
)
result = chain.invoke(input, config=config)
""",
    
    "tracing": """
# Enable LangSmith tracing
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "..."
os.environ["LANGCHAIN_PROJECT"] = "my-project"
"""
}


def get_pattern(pattern_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific pattern by name."""
    if pattern_name in CHAIN_PATTERNS:
        p = CHAIN_PATTERNS[pattern_name]
        return {
            "type": "chain",
            "name": p.name,
            "description": p.description,
            "code": p.code_example,
            "use_cases": p.use_cases
        }
    elif pattern_name in AGENT_PATTERNS:
        p = AGENT_PATTERNS[pattern_name]
        return {
            "type": "agent",
            "name": p.name,
            "description": p.description,
            "code": p.code_example,
            "tools": p.tools_required
        }
    return None


def list_patterns() -> Dict[str, List[str]]:
    """List all available patterns."""
    return {
        "chains": list(CHAIN_PATTERNS.keys()),
        "agents": list(AGENT_PATTERNS.keys()),
        "lcel": list(LCEL_PATTERNS.keys()),
        "best_practices": list(BEST_PRACTICES.keys())
    }


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LangChain Patterns")
    parser.add_argument("--list", action="store_true", help="List all patterns")
    parser.add_argument("--pattern", type=str, help="Get specific pattern")
    parser.add_argument("--lcel", type=str, help="Get LCEL pattern")
    parser.add_argument("--best-practice", type=str, help="Get best practice")
    
    args = parser.parse_args()
    
    if args.list:
        patterns = list_patterns()
        print(json.dumps(patterns, indent=2))
    
    elif args.pattern:
        pattern = get_pattern(args.pattern)
        if pattern:
            print(json.dumps(pattern, indent=2))
            print("\n--- Code Example ---")
            print(pattern["code"])
        else:
            print(f"Pattern '{args.pattern}' not found")
    
    elif args.lcel:
        if args.lcel in LCEL_PATTERNS:
            print(LCEL_PATTERNS[args.lcel])
        else:
            print(f"LCEL pattern '{args.lcel}' not found")
    
    elif args.best_practice:
        if args.best_practice in BEST_PRACTICES:
            print(BEST_PRACTICES[args.best_practice])
        else:
            print(f"Best practice '{args.best_practice}' not found")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
