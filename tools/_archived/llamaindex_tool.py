#!/usr/bin/env python3
"""
LlamaIndex Tool - Data Framework Patterns

Best-in-class RAG and data indexing patterns.
Addresses GAP-ORCH-005: LlamaIndex data framework.
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class IndexType(Enum):
    """LlamaIndex index types."""
    VECTOR = "vector"
    LIST = "list"
    TREE = "tree"
    KEYWORD = "keyword"
    KNOWLEDGE_GRAPH = "knowledge_graph"


class RetrieverType(Enum):
    """Retriever types."""
    SIMILARITY = "similarity"
    BM25 = "bm25"
    HYBRID = "hybrid"
    RECURSIVE = "recursive"
    AUTO_MERGE = "auto_merge"


@dataclass
class IndexPattern:
    """Index pattern definition."""
    name: str
    index_type: IndexType
    description: str
    code_example: str
    use_cases: List[str]


# Index patterns
INDEX_PATTERNS: Dict[str, IndexPattern] = {
    "vector_simple": IndexPattern(
        name="Simple Vector Index",
        index_type=IndexType.VECTOR,
        description="Basic vector index for semantic search",
        code_example="""
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

# Load documents
documents = SimpleDirectoryReader("./data").load_data()

# Create index
index = VectorStoreIndex.from_documents(documents)

# Query
query_engine = index.as_query_engine()
response = query_engine.query("What is the main topic?")
""",
        use_cases=["Document QA", "Knowledge bases", "Semantic search"]
    ),
    
    "vector_with_storage": IndexPattern(
        name="Vector Index with Persistence",
        index_type=IndexType.VECTOR,
        description="Persistent vector index with storage",
        code_example="""
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

# Setup ChromaDB
db = chromadb.PersistentClient(path="./chroma_db")
collection = db.get_or_create_collection("documents")
vector_store = ChromaVectorStore(chroma_collection=collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Create index
index = VectorStoreIndex.from_documents(
    documents, storage_context=storage_context
)

# Save
index.storage_context.persist(persist_dir="./storage")

# Load
from llama_index.core import load_index_from_storage
index = load_index_from_storage(storage_context)
""",
        use_cases=["Production RAG", "Large datasets", "Persistent storage"]
    ),
    
    "knowledge_graph": IndexPattern(
        name="Knowledge Graph Index",
        index_type=IndexType.KNOWLEDGE_GRAPH,
        description="Graph-based index for relationship queries",
        code_example="""
from llama_index.core import KnowledgeGraphIndex
from llama_index.core.graph_stores import SimpleGraphStore

# Create graph store
graph_store = SimpleGraphStore()

# Build knowledge graph
index = KnowledgeGraphIndex.from_documents(
    documents,
    max_triplets_per_chunk=2,
    graph_store=graph_store,
    include_embeddings=True
)

# Query with graph
query_engine = index.as_query_engine(
    include_text=True,
    retriever_mode="keyword",
)
""",
        use_cases=["Entity relationships", "Complex queries", "Graph reasoning"]
    )
}


# Retriever patterns
RETRIEVER_PATTERNS: Dict[str, str] = {
    "hybrid": """
from llama_index.core.retrievers import BM25Retriever, VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor

# BM25 retriever
bm25_retriever = BM25Retriever.from_defaults(index=index, similarity_top_k=5)

# Vector retriever
vector_retriever = VectorIndexRetriever(index=index, similarity_top_k=5)

# Hybrid retrieval
from llama_index.core.query_engine import SubQuestionQueryEngine
from llama_index.core.tools import QueryEngineTool

tools = [
    QueryEngineTool.from_defaults(
        query_engine=RetrieverQueryEngine.from_args(bm25_retriever),
        description="Keyword search"
    ),
    QueryEngineTool.from_defaults(
        query_engine=RetrieverQueryEngine.from_args(vector_retriever),
        description="Semantic search"
    )
]
""",
    
    "recursive": """
from llama_index.core.retrievers import RecursiveRetriever
from llama_index.core.query_engine import RetrieverQueryEngine

# Build node references
all_nodes_dict = {n.node_id: n for n in all_nodes}

# Recursive retriever
retriever = RecursiveRetriever(
    "vector",
    retriever_dict={"vector": index.as_retriever()},
    node_dict=all_nodes_dict,
)

query_engine = RetrieverQueryEngine.from_args(retriever)
""",
    
    "auto_merge": """
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.core.retrievers import AutoMergingRetriever

# Hierarchical parsing
node_parser = HierarchicalNodeParser.from_defaults(chunk_sizes=[2048, 512, 128])
nodes = node_parser.get_nodes_from_documents(documents)
leaf_nodes = get_leaf_nodes(nodes)

# Build with leaf nodes
index = VectorStoreIndex(leaf_nodes, storage_context=storage_context)

# Auto-merging retriever
base_retriever = index.as_retriever(similarity_top_k=6)
retriever = AutoMergingRetriever(
    base_retriever, storage_context, verbose=True
)
"""
}


# Agent patterns
AGENT_PATTERNS = {
    "react_agent": """
from llama_index.core.agent import ReActAgent
from llama_index.llms.anthropic import Anthropic
from llama_index.core.tools import QueryEngineTool

llm = Anthropic(model="claude-sonnet-4-20250514")

tools = [
    QueryEngineTool.from_defaults(
        query_engine=index.as_query_engine(),
        name="knowledge_base",
        description="Search the knowledge base"
    )
]

agent = ReActAgent.from_tools(tools, llm=llm, verbose=True)
response = agent.chat("What can you tell me about...")
""",
    
    "openai_agent": """
from llama_index.agent.openai import OpenAIAgent
from llama_index.llms.openai import OpenAI

llm = OpenAI(model="gpt-4")
agent = OpenAIAgent.from_tools(tools, llm=llm)
""",
    
    "multi_doc_agent": """
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import QueryEngineTool

# Create tool per document collection
tools = []
for name, index in doc_indices.items():
    tool = QueryEngineTool.from_defaults(
        query_engine=index.as_query_engine(),
        name=f"doc_{name}",
        description=f"Search {name} documentation"
    )
    tools.append(tool)

agent = ReActAgent.from_tools(tools, llm=llm, verbose=True)
"""
}


# Production patterns
PRODUCTION_PATTERNS = {
    "streaming": """
query_engine = index.as_query_engine(streaming=True)
streaming_response = query_engine.query("...")

for text in streaming_response.response_gen:
    print(text, end="")
""",
    
    "async": """
import asyncio

async def async_query():
    query_engine = index.as_query_engine()
    response = await query_engine.aquery("...")
    return response

# Run async
response = asyncio.run(async_query())
""",
    
    "observability": """
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler

llama_debug = LlamaDebugHandler(print_trace_on_end=True)
callback_manager = CallbackManager([llama_debug])

index = VectorStoreIndex.from_documents(
    documents, callback_manager=callback_manager
)
"""
}


def get_pattern(pattern_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific pattern."""
    if pattern_name in INDEX_PATTERNS:
        p = INDEX_PATTERNS[pattern_name]
        return {
            "type": "index",
            "name": p.name,
            "index_type": p.index_type.value,
            "description": p.description,
            "code": p.code_example,
            "use_cases": p.use_cases
        }
    return None


def list_patterns() -> Dict[str, List[str]]:
    """List all available patterns."""
    return {
        "index": list(INDEX_PATTERNS.keys()),
        "retriever": list(RETRIEVER_PATTERNS.keys()),
        "agent": list(AGENT_PATTERNS.keys()),
        "production": list(PRODUCTION_PATTERNS.keys())
    }


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LlamaIndex Patterns")
    parser.add_argument("--list", action="store_true", help="List all patterns")
    parser.add_argument("--index", type=str, help="Get index pattern")
    parser.add_argument("--retriever", type=str, help="Get retriever pattern")
    parser.add_argument("--agent", type=str, help="Get agent pattern")
    parser.add_argument("--production", type=str, help="Get production pattern")
    
    args = parser.parse_args()
    
    if args.list:
        print(json.dumps(list_patterns(), indent=2))
    
    elif args.index:
        pattern = get_pattern(args.index)
        if pattern:
            print(json.dumps(pattern, indent=2))
            print("\n--- Code Example ---")
            print(pattern["code"])
        else:
            print(f"Pattern '{args.index}' not found")
    
    elif args.retriever:
        if args.retriever in RETRIEVER_PATTERNS:
            print(RETRIEVER_PATTERNS[args.retriever])
        else:
            print(f"Retriever pattern '{args.retriever}' not found")
    
    elif args.agent:
        if args.agent in AGENT_PATTERNS:
            print(AGENT_PATTERNS[args.agent])
        else:
            print(f"Agent pattern '{args.agent}' not found")
    
    elif args.production:
        if args.production in PRODUCTION_PATTERNS:
            print(PRODUCTION_PATTERNS[args.production])
        else:
            print(f"Production pattern '{args.production}' not found")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
