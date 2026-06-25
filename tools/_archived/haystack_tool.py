#!/usr/bin/env python3
"""
Haystack Tool - Production RAG Patterns

End-to-end RAG framework patterns from deepset-ai.
Addresses GAP-ORCH-006: Haystack production RAG.
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class PipelineType(Enum):
    """Haystack pipeline types."""
    INDEXING = "indexing"
    QUERY = "query"
    CHAT = "chat"
    HYBRID = "hybrid"


@dataclass
class PipelinePattern:
    """Pipeline pattern definition."""
    name: str
    pipeline_type: PipelineType
    description: str
    code_example: str
    components: List[str]


# Pipeline patterns
PIPELINE_PATTERNS: Dict[str, PipelinePattern] = {
    "basic_rag": PipelinePattern(
        name="Basic RAG Pipeline",
        pipeline_type=PipelineType.QUERY,
        description="Simple retrieval-augmented generation",
        code_example="""
from haystack import Pipeline
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.components.builders import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.document_stores.in_memory import InMemoryDocumentStore

# Setup document store
document_store = InMemoryDocumentStore()

# Build pipeline
pipeline = Pipeline()
pipeline.add_component("retriever", InMemoryBM25Retriever(document_store=document_store))
pipeline.add_component("prompt_builder", PromptBuilder(template=\"\"\"
Given the following documents, answer the question.
Documents:
{% for doc in documents %}
{{ doc.content }}
{% endfor %}
Question: {{question}}
Answer:
\"\"\"))
pipeline.add_component("llm", OpenAIGenerator(model="gpt-4"))

# Connect components
pipeline.connect("retriever", "prompt_builder.documents")
pipeline.connect("prompt_builder", "llm")

# Run
result = pipeline.run({
    "retriever": {"query": "What is Haystack?"},
    "prompt_builder": {"question": "What is Haystack?"}
})
""",
        components=["Retriever", "PromptBuilder", "Generator"]
    ),
    
    "hybrid_retrieval": PipelinePattern(
        name="Hybrid Retrieval Pipeline",
        pipeline_type=PipelineType.HYBRID,
        description="Combine BM25 and embedding retrieval",
        code_example="""
from haystack import Pipeline
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever, InMemoryEmbeddingRetriever
from haystack.components.joiners import DocumentJoiner
from haystack.components.rankers import TransformersSimilarityRanker

pipeline = Pipeline()

# Add both retrievers
pipeline.add_component("bm25_retriever", InMemoryBM25Retriever(document_store))
pipeline.add_component("embedding_retriever", InMemoryEmbeddingRetriever(document_store))

# Join results
pipeline.add_component("joiner", DocumentJoiner())

# Re-rank combined results
pipeline.add_component("ranker", TransformersSimilarityRanker(model="cross-encoder/ms-marco-MiniLM-L-6-v2"))

# Connect
pipeline.connect("bm25_retriever", "joiner.documents")
pipeline.connect("embedding_retriever", "joiner.documents")
pipeline.connect("joiner", "ranker")
""",
        components=["BM25Retriever", "EmbeddingRetriever", "DocumentJoiner", "Ranker"]
    ),
    
    "indexing": PipelinePattern(
        name="Indexing Pipeline",
        pipeline_type=PipelineType.INDEXING,
        description="Document ingestion and indexing",
        code_example="""
from haystack import Pipeline
from haystack.components.converters import TextFileToDocument, PyPDFToDocument
from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack.components.embedders import SentenceTransformersDocumentEmbedder

pipeline = Pipeline()

# Converters
pipeline.add_component("converter", PyPDFToDocument())

# Preprocessing
pipeline.add_component("cleaner", DocumentCleaner())
pipeline.add_component("splitter", DocumentSplitter(split_by="sentence", split_length=3))

# Embedding
pipeline.add_component("embedder", SentenceTransformersDocumentEmbedder())

# Writing
pipeline.add_component("writer", DocumentWriter(document_store=document_store))

# Connect
pipeline.connect("converter", "cleaner")
pipeline.connect("cleaner", "splitter")
pipeline.connect("splitter", "embedder")
pipeline.connect("embedder", "writer")

# Run
pipeline.run({"converter": {"sources": ["document.pdf"]}})
""",
        components=["Converter", "Cleaner", "Splitter", "Embedder", "Writer"]
    ),
    
    "chat": PipelinePattern(
        name="Chat Pipeline",
        pipeline_type=PipelineType.CHAT,
        description="Conversational RAG with memory",
        code_example="""
from haystack import Pipeline
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.dataclasses import ChatMessage

pipeline = Pipeline()
pipeline.add_component("retriever", InMemoryBM25Retriever(document_store))
pipeline.add_component("llm", OpenAIChatGenerator(model="gpt-4"))

# Maintain conversation history
messages = []

def chat(user_message: str):
    # Retrieve context
    docs = pipeline.run({"retriever": {"query": user_message}})
    context = "\\n".join([d.content for d in docs["retriever"]["documents"]])
    
    # Build message with context
    system_msg = ChatMessage.from_system(f"Context: {context}")
    user_msg = ChatMessage.from_user(user_message)
    messages.extend([system_msg, user_msg])
    
    # Generate response
    result = pipeline.run({"llm": {"messages": messages}})
    assistant_msg = result["llm"]["replies"][0]
    messages.append(assistant_msg)
    
    return assistant_msg.content
""",
        components=["Retriever", "ChatGenerator", "Memory"]
    )
}


# Component patterns
COMPONENT_PATTERNS = {
    "custom_component": """
from haystack import component, Document
from typing import List

@component
class CustomProcessor:
    '''Custom document processor.'''
    
    @component.output_types(documents=List[Document])
    def run(self, documents: List[Document]) -> dict:
        processed = []
        for doc in documents:
            # Custom processing logic
            doc.content = doc.content.upper()
            processed.append(doc)
        return {"documents": processed}

# Use in pipeline
pipeline.add_component("processor", CustomProcessor())
""",
    
    "embedding_models": """
from haystack.components.embedders import (
    SentenceTransformersTextEmbedder,
    SentenceTransformersDocumentEmbedder,
    OpenAITextEmbedder,
    OpenAIDocumentEmbedder
)

# For queries (text)
text_embedder = SentenceTransformersTextEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")

# For documents
doc_embedder = SentenceTransformersDocumentEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")

# OpenAI embeddings
openai_embedder = OpenAITextEmbedder(model="text-embedding-3-small")
""",
    
    "document_stores": """
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack_integrations.document_stores.chroma import ChromaDocumentStore
from haystack_integrations.document_stores.pinecone import PineconeDocumentStore
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

# In-memory (development)
memory_store = InMemoryDocumentStore()

# Chroma (local persistence)
chroma_store = ChromaDocumentStore(persist_path="./chroma_db")

# Pinecone (cloud)
pinecone_store = PineconeDocumentStore(
    api_key="...",
    environment="...",
    index="my-index"
)

# Qdrant (self-hosted or cloud)
qdrant_store = QdrantDocumentStore(
    url="http://localhost:6333",
    index="documents"
)
"""
}


# Evaluation patterns
EVALUATION_PATTERNS = {
    "ragas": """
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

# Prepare evaluation data
eval_data = {
    "question": questions,
    "answer": answers,
    "contexts": contexts,
    "ground_truth": ground_truths
}

# Run evaluation
result = evaluate(
    eval_data,
    metrics=[faithfulness, answer_relevancy, context_precision]
)
print(result)
""",
    
    "pipeline_eval": """
from haystack.evaluation import EvaluationRunResult

# Run pipeline on test set
predictions = []
for question in test_questions:
    result = pipeline.run({"retriever": {"query": question}})
    predictions.append(result)

# Calculate metrics
eval_result = EvaluationRunResult(
    predictions=predictions,
    ground_truths=ground_truths
)
print(eval_result.calculate_metrics())
"""
}


def get_pipeline_pattern(name: str) -> Optional[Dict[str, Any]]:
    """Get a specific pipeline pattern."""
    if name in PIPELINE_PATTERNS:
        p = PIPELINE_PATTERNS[name]
        return {
            "name": p.name,
            "type": p.pipeline_type.value,
            "description": p.description,
            "code": p.code_example,
            "components": p.components
        }
    return None


def list_patterns() -> Dict[str, List[str]]:
    """List all available patterns."""
    return {
        "pipelines": list(PIPELINE_PATTERNS.keys()),
        "components": list(COMPONENT_PATTERNS.keys()),
        "evaluation": list(EVALUATION_PATTERNS.keys())
    }


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Haystack RAG Patterns")
    parser.add_argument("--list", action="store_true", help="List all patterns")
    parser.add_argument("--pipeline", type=str, help="Get pipeline pattern")
    parser.add_argument("--component", type=str, help="Get component pattern")
    parser.add_argument("--eval", type=str, help="Get evaluation pattern")
    
    args = parser.parse_args()
    
    if args.list:
        print(json.dumps(list_patterns(), indent=2))
    elif args.pipeline:
        pattern = get_pipeline_pattern(args.pipeline)
        if pattern:
            print(json.dumps(pattern, indent=2))
            print("\n--- Code ---")
            print(pattern["code"])
        else:
            print(f"Pipeline '{args.pipeline}' not found")
    elif args.component:
        if args.component in COMPONENT_PATTERNS:
            print(COMPONENT_PATTERNS[args.component])
        else:
            print(f"Component pattern '{args.component}' not found")
    elif args.eval:
        if args.eval in EVALUATION_PATTERNS:
            print(EVALUATION_PATTERNS[args.eval])
        else:
            print(f"Evaluation pattern '{args.eval}' not found")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
