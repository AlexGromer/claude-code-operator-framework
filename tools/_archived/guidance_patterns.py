#!/usr/bin/env python3
"""
Microsoft Guidance Patterns Tool (GAP-ORCH-017)

Provides patterns and utilities for Microsoft Guidance library -
a programming paradigm for controlling LLM generation with
constrained decoding and structured outputs.

Key Features:
- Constrained generation patterns
- Grammar-based output control
- Template syntax helpers
- Token healing and acceleration
- State management patterns

Usage:
    python guidance_patterns.py --pattern basic --show
    python guidance_patterns.py --list
    python guidance_patterns.py --validate template.txt
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
    """Categories of Guidance patterns."""
    BASIC = "basic"
    CONSTRAINED = "constrained"
    GRAMMAR = "grammar"
    STATEFUL = "stateful"
    ADVANCED = "advanced"


@dataclass
class GuidancePattern:
    """Represents a Guidance pattern template."""
    name: str
    category: PatternCategory
    description: str
    template: str
    python_code: str
    use_cases: List[str] = field(default_factory=list)
    requires_model: str = "any"  # any, chat, instruct, completion


# Guidance pattern templates
GUIDANCE_PATTERNS: Dict[str, GuidancePattern] = {
    "basic_generation": GuidancePattern(
        name="Basic Generation",
        category=PatternCategory.BASIC,
        description="Simple text generation with Guidance",
        template='''
{{#system~}}
You are a helpful assistant.
{{~/system}}

{{#user~}}
{{query}}
{{~/user}}

{{#assistant~}}
{{gen 'response' max_tokens=500}}
{{~/assistant}}
''',
        python_code='''
import guidance

# Load model
model = guidance.models.OpenAI("gpt-4")

# Create program
program = guidance("""
{{#system~}}
You are a helpful assistant.
{{~/system}}

{{#user~}}
{{query}}
{{~/user}}

{{#assistant~}}
{{gen 'response' max_tokens=500}}
{{~/assistant}}
""")

# Execute
result = program(query="What is Python?")
print(result["response"])
''',
        use_cases=[
            "Simple Q&A",
            "Basic chat completion",
            "Getting started with Guidance"
        ]
    ),

    "constrained_choice": GuidancePattern(
        name="Constrained Choice",
        category=PatternCategory.CONSTRAINED,
        description="Force model to choose from predefined options",
        template='''
{{#system~}}
You are a sentiment classifier.
{{~/system}}

{{#user~}}
Classify the sentiment of: "{{text}}"
{{~/user}}

{{#assistant~}}
The sentiment is: {{select 'sentiment' options=["positive", "negative", "neutral"]}}
{{~/assistant}}
''',
        python_code='''
import guidance

model = guidance.models.OpenAI("gpt-4")

classifier = guidance("""
{{#system~}}
You are a sentiment classifier.
{{~/system}}

{{#user~}}
Classify the sentiment of: "{{text}}"
{{~/user}}

{{#assistant~}}
The sentiment is: {{select 'sentiment' options=["positive", "negative", "neutral"]}}
{{~/assistant}}
""")

result = classifier(text="I love this product!")
print(f"Sentiment: {result['sentiment']}")  # Always one of the three options
''',
        use_cases=[
            "Classification tasks",
            "Multiple choice answers",
            "Constrained decision making"
        ]
    ),

    "json_output": GuidancePattern(
        name="JSON Output",
        category=PatternCategory.CONSTRAINED,
        description="Generate valid JSON with schema constraints",
        template='''
{{#system~}}
You extract structured data from text.
{{~/system}}

{{#user~}}
Extract person info from: "{{text}}"
{{~/user}}

{{#assistant~}}
{
    "name": "{{gen 'name' stop='"'}}",
    "age": {{gen 'age' pattern='[0-9]+'}},
    "occupation": "{{gen 'occupation' stop='"'}}"
}
{{~/assistant}}
''',
        python_code='''
import guidance

model = guidance.models.OpenAI("gpt-4")

extractor = guidance("""
{{#system~}}
You extract structured data from text.
{{~/system}}

{{#user~}}
Extract person info from: "{{text}}"
{{~/user}}

{{#assistant~}}
{
    "name": "{{gen 'name' stop='"'}}",
    "age": {{gen 'age' pattern='[0-9]+'}},
    "occupation": "{{gen 'occupation' stop='"'}}"
}
{{~/assistant}}
""")

result = extractor(text="John Smith is a 35-year-old software engineer.")
person = {
    "name": result["name"],
    "age": int(result["age"]),
    "occupation": result["occupation"]
}
print(json.dumps(person, indent=2))
''',
        use_cases=[
            "Structured data extraction",
            "API response generation",
            "Form filling"
        ]
    ),

    "grammar_regex": GuidancePattern(
        name="Regex Pattern Matching",
        category=PatternCategory.GRAMMAR,
        description="Constrain generation using regex patterns",
        template='''
{{#assistant~}}
Email: {{gen 'email' pattern='[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}'}}
Phone: {{gen 'phone' pattern='\\+?[0-9]{1,3}[-.\\s]?\\(?[0-9]{1,4}\\)?[-.\\s]?[0-9]{1,4}[-.\\s]?[0-9]{1,9}'}}
Date: {{gen 'date' pattern='[0-9]{4}-[0-9]{2}-[0-9]{2}'}}
{{~/assistant}}
''',
        python_code='''
import guidance

model = guidance.models.OpenAI("gpt-4")

generator = guidance("""
Generate contact information:

Email: {{gen 'email' pattern='[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}'}}
Phone: {{gen 'phone' pattern='\\+?[0-9]{1,3}[-.\\s]?\\(?[0-9]{1,4}\\)?[-.\\s]?[0-9]{1,4}[-.\\s]?[0-9]{1,9}'}}
Date: {{gen 'date' pattern='[0-9]{4}-[0-9]{2}-[0-9]{2}'}}
""")

result = generator()
print(f"Email: {result['email']}")
print(f"Phone: {result['phone']}")
print(f"Date: {result['date']}")
''',
        use_cases=[
            "Structured data generation",
            "Format enforcement",
            "Validation-safe outputs"
        ]
    ),

    "chain_of_thought": GuidancePattern(
        name="Chain of Thought",
        category=PatternCategory.ADVANCED,
        description="Guided reasoning with explicit thought steps",
        template='''
{{#system~}}
You solve math problems step by step.
{{~/system}}

{{#user~}}
Solve: {{problem}}
{{~/user}}

{{#assistant~}}
Let me solve this step by step:

Step 1: {{gen 'step1' stop='\\n'}}
Step 2: {{gen 'step2' stop='\\n'}}
Step 3: {{gen 'step3' stop='\\n'}}

Therefore, the answer is: {{gen 'answer' pattern='[0-9.]+'}}
{{~/assistant}}
''',
        python_code='''
import guidance

model = guidance.models.OpenAI("gpt-4")

solver = guidance("""
{{#system~}}
You solve math problems step by step.
{{~/system}}

{{#user~}}
Solve: {{problem}}
{{~/user}}

{{#assistant~}}
Let me solve this step by step:

Step 1: {{gen 'step1' stop='\\n'}}
Step 2: {{gen 'step2' stop='\\n'}}
Step 3: {{gen 'step3' stop='\\n'}}

Therefore, the answer is: {{gen 'answer' pattern='[0-9.]+'}}
{{~/assistant}}
""")

result = solver(problem="If a train travels at 60 mph for 2.5 hours, how far does it travel?")
print(f"Step 1: {result['step1']}")
print(f"Step 2: {result['step2']}")
print(f"Step 3: {result['step3']}")
print(f"Answer: {result['answer']}")
''',
        use_cases=[
            "Math problem solving",
            "Logical reasoning",
            "Explainable AI"
        ]
    ),

    "stateful_loop": GuidancePattern(
        name="Stateful Loop",
        category=PatternCategory.STATEFUL,
        description="Generate variable number of items with state",
        template='''
{{#system~}}
You generate a list of items based on the topic.
{{~/system}}

{{#user~}}
List 3 {{topic}}:
{{~/user}}

{{#assistant~}}
{{#geneach 'items' num_iterations=3}}
{{@index + 1}}. {{gen 'this' stop='\\n'}}
{{/geneach}}
{{~/assistant}}
''',
        python_code='''
import guidance

model = guidance.models.OpenAI("gpt-4")

list_generator = guidance("""
{{#system~}}
You generate a list of items based on the topic.
{{~/system}}

{{#user~}}
List 3 {{topic}}:
{{~/user}}

{{#assistant~}}
{{#geneach 'items' num_iterations=3}}
{{@index + 1}}. {{gen 'this' stop='\\n'}}
{{/geneach}}
{{~/assistant}}
""")

result = list_generator(topic="programming languages")
for i, item in enumerate(result["items"], 1):
    print(f"{i}. {item}")
''',
        use_cases=[
            "List generation",
            "Multi-item outputs",
            "Dynamic content creation"
        ]
    ),

    "conditional_generation": GuidancePattern(
        name="Conditional Generation",
        category=PatternCategory.STATEFUL,
        description="Branch generation based on conditions",
        template='''
{{#system~}}
You are a helpful assistant that adapts to user needs.
{{~/system}}

{{#user~}}
I need help with {{task_type}}.
{{~/user}}

{{#assistant~}}
{{#if task_type == "code"}}
I'll help you with coding. Here's a solution:
```{{gen 'language' stop='\\n'}}
{{gen 'code' stop='```'}}
```
{{else if task_type == "writing"}}
I'll help you with writing. Here's my suggestion:
{{gen 'text' max_tokens=200}}
{{else}}
I'll provide general assistance:
{{gen 'response' max_tokens=150}}
{{/if}}
{{~/assistant}}
''',
        python_code='''
import guidance

model = guidance.models.OpenAI("gpt-4")

assistant = guidance("""
{{#system~}}
You are a helpful assistant that adapts to user needs.
{{~/system}}

{{#user~}}
I need help with {{task_type}}.
{{~/user}}

{{#assistant~}}
{{#if task_type == "code"}}
I'll help you with coding. Here's a solution:
```{{gen 'language' stop='\\n'}}
{{gen 'code' stop='```'}}
```
{{else if task_type == "writing"}}
I'll help you with writing. Here's my suggestion:
{{gen 'text' max_tokens=200}}
{{else}}
I'll provide general assistance:
{{gen 'response' max_tokens=150}}
{{/if}}
{{~/assistant}}
""")

# Different outputs based on task_type
code_result = assistant(task_type="code")
writing_result = assistant(task_type="writing")
''',
        use_cases=[
            "Adaptive responses",
            "Multi-modal assistants",
            "Dynamic workflows"
        ]
    ),

    "hidden_reasoning": GuidancePattern(
        name="Hidden Reasoning",
        category=PatternCategory.ADVANCED,
        description="Generate internal reasoning that is not shown to user",
        template='''
{{#system~}}
You are an expert analyst. Think through problems carefully.
{{~/system}}

{{#user~}}
{{question}}
{{~/user}}

{{#assistant~}}
{{#block hidden=True}}
Let me think about this...
{{gen 'reasoning' max_tokens=300}}
{{/block}}

Based on my analysis: {{gen 'answer' max_tokens=150}}
{{~/assistant}}
''',
        python_code='''
import guidance

model = guidance.models.OpenAI("gpt-4")

analyst = guidance("""
{{#system~}}
You are an expert analyst. Think through problems carefully.
{{~/system}}

{{#user~}}
{{question}}
{{~/user}}

{{#assistant~}}
{{#block hidden=True}}
Let me think about this...
{{gen 'reasoning' max_tokens=300}}
{{/block}}

Based on my analysis: {{gen 'answer' max_tokens=150}}
{{~/assistant}}
""")

result = analyst(question="What are the pros and cons of microservices?")
print(f"Internal reasoning: {result['reasoning']}")  # Available programmatically
print(f"User-facing answer: {result['answer']}")     # What user sees
''',
        use_cases=[
            "Complex analysis",
            "Reasoning transparency",
            "Debugging LLM decisions"
        ]
    ),

    "tool_use": GuidancePattern(
        name="Tool Use Pattern",
        category=PatternCategory.ADVANCED,
        description="Integrate external tool calls within generation",
        template='''
{{#system~}}
You can use tools to help answer questions.
Available tools: calculator, search
{{~/system}}

{{#user~}}
{{question}}
{{~/user}}

{{#assistant~}}
I need to use a tool for this.

Tool: {{select 'tool' options=["calculator", "search", "none"]}}
{{#if tool != "none"}}
Query: {{gen 'query' stop='\\n'}}
{{/if}}

{{#await 'tool_result'}}
Based on the result: {{gen 'response' max_tokens=200}}
{{~/assistant}}
''',
        python_code='''
import guidance

model = guidance.models.OpenAI("gpt-4")

# Tool functions
def calculator(query):
    try:
        return str(eval(query))  # Simplified - use safer eval in production
    except Exception:
        return "Error in calculation"

def search(query):
    return f"Search results for: {query}"  # Mock

# Create program
agent = guidance("""
{{#system~}}
You can use tools to help answer questions.
Available tools: calculator, search
{{~/system}}

{{#user~}}
{{question}}
{{~/user}}

{{#assistant~}}
I need to use a tool for this.

Tool: {{select 'tool' options=["calculator", "search", "none"]}}
{{#if tool != "none"}}
Query: {{gen 'query' stop='\\n'}}
{{/if}}
{{~/assistant}}
""")

# Execute with tool injection
result = agent(question="What is 15 * 23?")
if result["tool"] == "calculator":
    tool_result = calculator(result["query"])
    # Continue generation with result
''',
        use_cases=[
            "Tool-augmented generation",
            "Agent workflows",
            "External API integration"
        ]
    ),

    "few_shot": GuidancePattern(
        name="Few-Shot Learning",
        category=PatternCategory.BASIC,
        description="Dynamic few-shot examples within template",
        template='''
{{#system~}}
You are a helpful assistant that follows examples.
{{~/system}}

{{#each examples}}
{{#user~}}
Input: {{this.input}}
{{~/user}}

{{#assistant~}}
Output: {{this.output}}
{{~/assistant}}
{{/each}}

{{#user~}}
Input: {{new_input}}
{{~/user}}

{{#assistant~}}
Output: {{gen 'output' stop='\\n'}}
{{~/assistant}}
''',
        python_code='''
import guidance

model = guidance.models.OpenAI("gpt-4")

few_shot = guidance("""
{{#system~}}
You are a helpful assistant that follows examples.
{{~/system}}

{{#each examples}}
{{#user~}}
Input: {{this.input}}
{{~/user}}

{{#assistant~}}
Output: {{this.output}}
{{~/assistant}}
{{/each}}

{{#user~}}
Input: {{new_input}}
{{~/user}}

{{#assistant~}}
Output: {{gen 'output' stop='\\n'}}
{{~/assistant}}
""")

examples = [
    {"input": "cat", "output": "animal"},
    {"input": "rose", "output": "flower"},
    {"input": "python", "output": "programming language"}
]

result = few_shot(examples=examples, new_input="javascript")
print(f"Output: {result['output']}")  # Should be "programming language"
''',
        use_cases=[
            "Classification with examples",
            "Style matching",
            "In-context learning"
        ]
    ),
}


@dataclass
class ValidationResult:
    """Result of template validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    gen_blocks: List[str] = field(default_factory=list)


class GuidanceValidator:
    """Validates Guidance templates."""

    # Guidance syntax patterns
    VARIABLE_PATTERN = re.compile(r'\{\{(\w+)\}\}')
    GEN_PATTERN = re.compile(r"\{\{gen\s+'(\w+)'")
    SELECT_PATTERN = re.compile(r"\{\{select\s+'(\w+)'")
    BLOCK_PATTERN = re.compile(r'\{\{#(\w+)')
    END_BLOCK_PATTERN = re.compile(r'\{\{/(\w+)\}\}')

    def validate(self, template: str) -> ValidationResult:
        """Validate a Guidance template."""
        result = ValidationResult(valid=True)

        # Extract variables
        result.variables = self.VARIABLE_PATTERN.findall(template)

        # Extract gen blocks
        result.gen_blocks = self.GEN_PATTERN.findall(template)
        result.gen_blocks.extend(self.SELECT_PATTERN.findall(template))

        # Check block matching
        open_blocks = self.BLOCK_PATTERN.findall(template)
        close_blocks = self.END_BLOCK_PATTERN.findall(template)

        # Filter out self-closing blocks
        block_types = {'system', 'user', 'assistant', 'if', 'each', 'geneach', 'block', 'await'}
        open_count = {b: 0 for b in block_types}
        close_count = {b: 0 for b in block_types}

        for b in open_blocks:
            if b in block_types:
                open_count[b] += 1

        for b in close_blocks:
            if b in block_types:
                close_count[b] += 1

        for block_type in block_types:
            if open_count[block_type] != close_count[block_type]:
                result.errors.append(
                    f"Unmatched {block_type} blocks: {open_count[block_type]} open, "
                    f"{close_count[block_type]} close"
                )
                result.valid = False

        # Check for common issues
        if '{{gen' in template and 'stop=' not in template and 'max_tokens=' not in template:
            result.warnings.append(
                "gen block without stop or max_tokens - generation may be unbounded"
            )

        if '{{select' in template and 'options=' not in template:
            result.errors.append("select block requires options parameter")
            result.valid = False

        return result


def list_patterns(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all available patterns."""
    patterns = []
    for name, pattern in GUIDANCE_PATTERNS.items():
        if category and pattern.category.value != category:
            continue
        patterns.append({
            "name": name,
            "display_name": pattern.name,
            "category": pattern.category.value,
            "description": pattern.description,
            "use_cases": pattern.use_cases
        })
    return patterns


def get_pattern(name: str) -> Optional[GuidancePattern]:
    """Get a specific pattern by name."""
    return GUIDANCE_PATTERNS.get(name)


def show_pattern(name: str, include_code: bool = True) -> str:
    """Display a pattern with template and optional code."""
    pattern = get_pattern(name)
    if not pattern:
        return f"Pattern '{name}' not found"

    output = [
        f"# {pattern.name}",
        f"Category: {pattern.category.value}",
        f"Description: {pattern.description}",
        "",
        "## Template",
        "```handlebars",
        pattern.template.strip(),
        "```",
    ]

    if include_code:
        output.extend([
            "",
            "## Python Code",
            "```python",
            pattern.python_code.strip(),
            "```"
        ])

    output.extend([
        "",
        "## Use Cases",
        *[f"- {uc}" for uc in pattern.use_cases]
    ])

    return "\n".join(output)


def validate_template(template: str) -> ValidationResult:
    """Validate a Guidance template string."""
    validator = GuidanceValidator()
    return validator.validate(template)


def get_statistics() -> Dict[str, Any]:
    """Get statistics about available patterns."""
    stats = {
        "total_patterns": len(GUIDANCE_PATTERNS),
        "by_category": {},
        "total_use_cases": 0
    }

    for pattern in GUIDANCE_PATTERNS.values():
        cat = pattern.category.value
        stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
        stats["total_use_cases"] += len(pattern.use_cases)

    return stats


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Microsoft Guidance Patterns Tool"
    )
    parser.add_argument("--list", action="store_true", help="List all patterns")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--pattern", help="Show specific pattern")
    parser.add_argument("--show", action="store_true", help="Show pattern details")
    parser.add_argument("--validate", help="Validate template file")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.list:
        patterns = list_patterns(args.category)
        if args.json:
            print(json.dumps(patterns, indent=2))
        else:
            print(f"\n{'='*60}")
            print("MICROSOFT GUIDANCE PATTERNS")
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
                        "template": pattern.template,
                        "python_code": pattern.python_code,
                        "use_cases": pattern.use_cases
                    }, indent=2))
                else:
                    print(pattern.template)
            else:
                print(f"Pattern '{args.pattern}' not found")
                sys.exit(1)

    elif args.validate:
        template_path = Path(args.validate)
        if not template_path.exists():
            print(f"File not found: {args.validate}")
            sys.exit(1)

        template = template_path.read_text()
        result = validate_template(template)

        if args.json:
            print(json.dumps({
                "valid": result.valid,
                "errors": result.errors,
                "warnings": result.warnings,
                "variables": result.variables,
                "gen_blocks": result.gen_blocks
            }, indent=2))
        else:
            print(f"\nValidation: {'✓ PASSED' if result.valid else '✗ FAILED'}")
            if result.errors:
                print("\nErrors:")
                for e in result.errors:
                    print(f"  ✗ {e}")
            if result.warnings:
                print("\nWarnings:")
                for w in result.warnings:
                    print(f"  ⚠ {w}")
            print(f"\nVariables found: {', '.join(result.variables) or 'none'}")
            print(f"Gen blocks: {', '.join(result.gen_blocks) or 'none'}")

    elif args.stats:
        stats = get_statistics()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"\n{'='*40}")
            print("GUIDANCE PATTERNS STATISTICS")
            print(f"{'='*40}")
            print(f"Total patterns: {stats['total_patterns']}")
            print(f"Total use cases: {stats['total_use_cases']}")
            print("\nBy category:")
            for cat, count in stats['by_category'].items():
                print(f"  {cat}: {count}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
