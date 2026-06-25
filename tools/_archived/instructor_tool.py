#!/usr/bin/env python3
"""
Instructor Tool - Structured Output Patterns

Pydantic-based structured output extraction from LLMs.
Addresses GAP-ORCH-014: Instructor structured outputs.
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class ExtractionMode(Enum):
    """Extraction modes."""
    SIMPLE = "simple"
    PARALLEL = "parallel"
    STREAMING = "streaming"
    ITERABLE = "iterable"
    PARTIAL = "partial"


# Extraction patterns
EXTRACTION_PATTERNS: Dict[str, str] = {
    "basic": """
import instructor
from pydantic import BaseModel
from anthropic import Anthropic

# Patch the client
client = instructor.from_anthropic(Anthropic())

class UserInfo(BaseModel):
    name: str
    age: int
    email: str

# Extract structured data
user = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "John is 30 years old, email john@example.com"}],
    response_model=UserInfo
)

print(user.name)  # "John"
print(user.age)   # 30
""",
    
    "with_validation": """
import instructor
from pydantic import BaseModel, field_validator
from anthropic import Anthropic

client = instructor.from_anthropic(Anthropic())

class UserInfo(BaseModel):
    name: str
    age: int
    
    @field_validator('age')
    @classmethod
    def validate_age(cls, v):
        if v < 0 or v > 150:
            raise ValueError('Age must be between 0 and 150')
        return v

# Instructor will retry if validation fails
user = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    max_retries=3,  # Retry on validation failure
    messages=[{"role": "user", "content": "Extract: John is 30"}],
    response_model=UserInfo
)
""",
    
    "parallel": """
import instructor
from pydantic import BaseModel
from typing import List
import asyncio

client = instructor.from_anthropic(Anthropic())

class Person(BaseModel):
    name: str
    role: str

async def extract_people(texts: List[str]) -> List[Person]:
    tasks = [
        client.messages.create_async(
            model="claude-sonnet-4-20250514",
            messages=[{"role": "user", "content": text}],
            response_model=Person
        )
        for text in texts
    ]
    return await asyncio.gather(*tasks)

# Run parallel extraction
people = asyncio.run(extract_people(["John is a developer", "Jane is a designer"]))
""",
    
    "streaming": """
import instructor
from pydantic import BaseModel
from typing import List

client = instructor.from_anthropic(Anthropic())

class Report(BaseModel):
    title: str
    sections: List[str]
    conclusion: str

# Stream partial results
for partial in client.messages.create_partial(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "Write a report about AI"}],
    response_model=Report
):
    print(f"Title: {partial.title}")
    print(f"Sections so far: {len(partial.sections or [])}")
""",
    
    "iterable": """
import instructor
from pydantic import BaseModel

client = instructor.from_anthropic(Anthropic())

class Task(BaseModel):
    title: str
    priority: int
    
# Stream multiple objects
for task in client.messages.create_iterable(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "List 5 tasks for a software project"}],
    response_model=Task
):
    print(f"Task: {task.title} (Priority: {task.priority})")
""",
    
    "complex_nested": """
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Task(BaseModel):
    title: str
    priority: Priority
    assignee: Optional[str] = None

class Project(BaseModel):
    name: str
    description: str
    tasks: List[Task]
    
# Extract nested structure
project = client.messages.create(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "Create a project plan for building a website"}],
    response_model=Project
)
"""
}


# Model configurations
MODEL_CONFIGS = {
    "anthropic": """
import instructor
from anthropic import Anthropic

client = instructor.from_anthropic(Anthropic())
""",
    
    "openai": """
import instructor
from openai import OpenAI

client = instructor.from_openai(OpenAI())
""",
    
    "litellm": """
import instructor
import litellm

client = instructor.from_litellm(litellm.completion)

# Use any model via litellm
result = client(
    model="anthropic/claude-sonnet-4-20250514",
    messages=[...],
    response_model=MyModel
)
""",
    
    "ollama": """
import instructor
from openai import OpenAI

# Ollama with OpenAI-compatible API
client = instructor.from_openai(
    OpenAI(base_url="http://localhost:11434/v1", api_key="ollama"),
    mode=instructor.Mode.JSON
)
"""
}


# Advanced patterns
ADVANCED_PATTERNS = {
    "retry_logic": """
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def extract_with_retry(text: str) -> UserInfo:
    return client.messages.create(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": text}],
        response_model=UserInfo
    )
""",
    
    "caching": """
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def cached_extract(text_hash: str, text: str) -> UserInfo:
    return client.messages.create(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": text}],
        response_model=UserInfo
    )

def extract(text: str) -> UserInfo:
    text_hash = hashlib.md5(text.encode()).hexdigest()
    return cached_extract(text_hash, text)
""",
    
    "batch_processing": """
from concurrent.futures import ThreadPoolExecutor
from typing import List

def batch_extract(texts: List[str], max_workers: int = 5) -> List[UserInfo]:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(
            lambda t: client.messages.create(
                model="claude-sonnet-4-20250514",
                messages=[{"role": "user", "content": t}],
                response_model=UserInfo
            ),
            texts
        ))
    return results
"""
}


def list_patterns() -> Dict[str, List[str]]:
    """List all available patterns."""
    return {
        "extraction": list(EXTRACTION_PATTERNS.keys()),
        "models": list(MODEL_CONFIGS.keys()),
        "advanced": list(ADVANCED_PATTERNS.keys())
    }


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Instructor Patterns")
    parser.add_argument("--list", action="store_true", help="List all patterns")
    parser.add_argument("--extraction", type=str, help="Get extraction pattern")
    parser.add_argument("--model", type=str, help="Get model config")
    parser.add_argument("--advanced", type=str, help="Get advanced pattern")
    
    args = parser.parse_args()
    
    if args.list:
        print(json.dumps(list_patterns(), indent=2))
    elif args.extraction:
        if args.extraction in EXTRACTION_PATTERNS:
            print(EXTRACTION_PATTERNS[args.extraction])
        else:
            print(f"Pattern '{args.extraction}' not found")
    elif args.model:
        if args.model in MODEL_CONFIGS:
            print(MODEL_CONFIGS[args.model])
        else:
            print(f"Model config '{args.model}' not found")
    elif args.advanced:
        if args.advanced in ADVANCED_PATTERNS:
            print(ADVANCED_PATTERNS[args.advanced])
        else:
            print(f"Advanced pattern '{args.advanced}' not found")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
