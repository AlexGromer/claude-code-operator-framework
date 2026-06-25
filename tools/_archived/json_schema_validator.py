#!/usr/bin/env python3
"""
JSON Schema Validator (GAP-STRUCT-GEN-001)

Validates LLM outputs against JSON schemas.
Supports structured generation validation.

Usage:
    python json_schema_validator.py --validate '{"name": "test"}' --schema schema.json
    python json_schema_validator.py --extract "text with {json}"
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
RESULTS_FILE = DATA_DIR / "json_validation.jsonl"

# Common schemas for LLM outputs
BUILTIN_SCHEMAS = {
    "tool_call": {
        "type": "object",
        "required": ["name", "parameters"],
        "properties": {
            "name": {"type": "string"},
            "parameters": {"type": "object"},
        },
    },
    "function_call": {
        "type": "object",
        "required": ["function", "args"],
        "properties": {
            "function": {"type": "string"},
            "args": {"type": "object"},
        },
    },
    "structured_response": {
        "type": "object",
        "required": ["status", "data"],
        "properties": {
            "status": {"type": "string", "enum": ["success", "error"]},
            "data": {"type": ["object", "array", "null"]},
            "message": {"type": "string"},
        },
    },
    "code_review": {
        "type": "object",
        "required": ["issues"],
        "properties": {
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["severity", "message"],
                    "properties": {
                        "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                        "message": {"type": "string"},
                        "line": {"type": "integer"},
                        "suggestion": {"type": "string"},
                    },
                },
            },
            "summary": {"type": "string"},
        },
    },
}


def validate_type(value: Any, expected_type: Any) -> bool:
    """Validate value against expected type."""
    if isinstance(expected_type, list):
        return any(validate_type(value, t) for t in expected_type)

    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }

    if expected_type in type_map:
        return isinstance(value, type_map[expected_type])
    return True


def validate_schema(data: Any, schema: Dict, path: str = "") -> List[Dict]:
    """
    Validate data against JSON schema.

    Returns list of validation errors.
    """
    errors = []

    if schema is None:
        return errors

    # Type check
    if "type" in schema:
        if not validate_type(data, schema["type"]):
            errors.append({
                "path": path or "root",
                "error": f"Type mismatch: expected {schema['type']}, got {type(data).__name__}",
            })
            return errors  # Can't continue if type is wrong

    # Enum check
    if "enum" in schema:
        if data not in schema["enum"]:
            errors.append({
                "path": path or "root",
                "error": f"Value not in enum: {data} not in {schema['enum']}",
            })

    # Object validation
    if isinstance(data, dict):
        # Required fields
        if "required" in schema:
            for field in schema["required"]:
                if field not in data:
                    errors.append({
                        "path": f"{path}.{field}" if path else field,
                        "error": f"Missing required field: {field}",
                    })

        # Property validation
        if "properties" in schema:
            for key, value in data.items():
                if key in schema["properties"]:
                    prop_path = f"{path}.{key}" if path else key
                    errors.extend(validate_schema(value, schema["properties"][key], prop_path))

    # Array validation
    if isinstance(data, list) and "items" in schema:
        for i, item in enumerate(data):
            item_path = f"{path}[{i}]"
            errors.extend(validate_schema(item, schema["items"], item_path))

    # String constraints
    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append({"path": path, "error": f"String too short: {len(data)} < {schema['minLength']}"})
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            errors.append({"path": path, "error": f"String too long: {len(data)} > {schema['maxLength']}"})
        if "pattern" in schema and not re.match(schema["pattern"], data):
            errors.append({"path": path, "error": f"Pattern mismatch: {schema['pattern']}"})

    # Number constraints
    if isinstance(data, (int, float)):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append({"path": path, "error": f"Value below minimum: {data} < {schema['minimum']}"})
        if "maximum" in schema and data > schema["maximum"]:
            errors.append({"path": path, "error": f"Value above maximum: {data} > {schema['maximum']}"})

    return errors


def extract_json(text: str) -> List[Dict]:
    """Extract JSON objects from text."""
    results = []

    # Try to find JSON in code blocks
    code_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
    for match in re.finditer(code_block_pattern, text):
        try:
            data = json.loads(match.group(1).strip())
            results.append({"source": "code_block", "data": data})
        except Exception:
            pass

    # Try to find standalone JSON objects
    brace_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    for match in re.finditer(brace_pattern, text):
        try:
            data = json.loads(match.group())
            results.append({"source": "inline", "data": data})
        except Exception:
            pass

    # Try to find JSON arrays
    bracket_pattern = r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'
    for match in re.finditer(bracket_pattern, text):
        try:
            data = json.loads(match.group())
            results.append({"source": "array", "data": data})
        except Exception:
            pass

    return results


def validate_llm_output(output: str, schema_name: str = None, schema: Dict = None) -> Dict:
    """Validate LLM output against schema."""
    result = {
        "timestamp": datetime.now().isoformat(),
        "valid": False,
        "extracted": [],
        "errors": [],
    }

    # Get schema
    if schema is None and schema_name:
        schema = BUILTIN_SCHEMAS.get(schema_name)
        if not schema:
            result["errors"].append({"error": f"Unknown schema: {schema_name}"})
            return result

    # Try to parse as JSON directly
    try:
        data = json.loads(output)
        result["extracted"].append({"source": "direct", "data": data})
    except Exception:
        # Extract JSON from text
        result["extracted"] = extract_json(output)

    if not result["extracted"]:
        result["errors"].append({"error": "No valid JSON found in output"})
        return result

    # Validate against schema if provided
    if schema:
        for item in result["extracted"]:
            errors = validate_schema(item["data"], schema)
            item["validation_errors"] = errors
            if not errors:
                result["valid"] = True
    else:
        # Just check if JSON is valid
        result["valid"] = True

    return result


def save_result(result: Dict):
    """Save validation result."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "a") as f:
        f.write(json.dumps(result) + "\n")


def print_result(result: Dict):
    """Print validation result."""
    print("\n" + "="*60)
    print("JSON SCHEMA VALIDATION")
    print("="*60)

    status = "✅ VALID" if result["valid"] else "❌ INVALID"
    print(f"\nStatus: {status}")
    print(f"JSON objects found: {len(result['extracted'])}")

    for i, item in enumerate(result["extracted"], 1):
        print(f"\n--- Object {i} ({item['source']}) ---")
        print(json.dumps(item["data"], indent=2)[:500])

        if "validation_errors" in item and item["validation_errors"]:
            print("\nValidation errors:")
            for err in item["validation_errors"]:
                print(f"  ❌ {err['path']}: {err['error']}")

    if result["errors"]:
        print("\nGeneral errors:")
        for err in result["errors"]:
            print(f"  ❌ {err.get('error', err)}")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="JSON Schema Validator")
    parser.add_argument("--validate", "-v", help="JSON string or text to validate")
    parser.add_argument("--schema", "-s", help="Schema name or file path")
    parser.add_argument("--extract", "-e", help="Extract JSON from text")
    parser.add_argument("--list-schemas", "-l", action="store_true", help="List built-in schemas")
    parser.add_argument("--file", "-f", help="Read input from file")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--save", action="store_true", help="Save result")

    args = parser.parse_args()

    if args.list_schemas:
        print("\nBuilt-in schemas:")
        for name, schema in BUILTIN_SCHEMAS.items():
            print(f"\n  {name}:")
            print(f"    Required: {schema.get('required', [])}")
        return 0

    # Get input
    if args.file:
        text = Path(args.file).read_text()
    elif args.validate:
        text = args.validate
    elif args.extract:
        text = args.extract
    else:
        parser.print_help()
        return 0

    # Get schema
    schema = None
    if args.schema:
        if args.schema in BUILTIN_SCHEMAS:
            schema = BUILTIN_SCHEMAS[args.schema]
        elif Path(args.schema).exists():
            schema = json.loads(Path(args.schema).read_text())
        else:
            print(f"Schema not found: {args.schema}")
            return 1

    # Validate
    if args.extract:
        extracted = extract_json(text)
        result = {"extracted": extracted, "count": len(extracted)}
    else:
        result = validate_llm_output(text, schema=schema)

    if args.save:
        save_result(result)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_result(result)

    return 0 if result.get("valid", True) else 1


if __name__ == "__main__":
    sys.exit(main())
