#!/usr/bin/env python3
"""
Evaluation Dataset Manager (GAP-TEST-FIX-001)

Manages evaluation datasets for LLM testing.
Supports versioning, golden sets, and test case management.

Usage:
    python eval_dataset_manager.py --list
    python eval_dataset_manager.py --create dataset_name
    python eval_dataset_manager.py --add dataset_name --case test_case.json
"""

import argparse
import json
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
DATASETS_DIR = DATA_DIR / "datasets"


@dataclass
class TestCase:
    """Individual test case."""
    id: str
    input: str
    expected_output: Optional[str] = None
    expected_contains: List[str] = None
    expected_not_contains: List[str] = None
    tags: List[str] = None
    metadata: Dict = None


@dataclass
class Dataset:
    """Evaluation dataset."""
    name: str
    version: str
    created: str
    updated: str
    description: str
    cases: List[Dict]
    tags: List[str]
    hash: str


def ensure_dirs():
    """Ensure directories exist."""
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)


def compute_hash(cases: List[Dict]) -> str:
    """Compute hash of test cases."""
    content = json.dumps(cases, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def load_dataset(name: str) -> Optional[Dataset]:
    """Load dataset by name."""
    dataset_file = DATASETS_DIR / f"{name}.json"
    if not dataset_file.exists():
        return None

    data = json.loads(dataset_file.read_text())
    return Dataset(**data)


def save_dataset(dataset: Dataset):
    """Save dataset to file."""
    ensure_dirs()
    dataset_file = DATASETS_DIR / f"{dataset.name}.json"

    # Update hash
    dataset.hash = compute_hash(dataset.cases)
    dataset.updated = datetime.now().isoformat()

    with open(dataset_file, "w") as f:
        json.dump(asdict(dataset), f, indent=2)


def create_dataset(name: str, description: str = "", tags: List[str] = None) -> Dataset:
    """Create new dataset."""
    now = datetime.now().isoformat()
    dataset = Dataset(
        name=name,
        version="1.0.0",
        created=now,
        updated=now,
        description=description,
        cases=[],
        tags=tags or [],
        hash="",
    )
    save_dataset(dataset)
    return dataset


def add_test_case(dataset_name: str, case: TestCase) -> bool:
    """Add test case to dataset."""
    dataset = load_dataset(dataset_name)
    if not dataset:
        return False

    # Check for duplicates
    for existing in dataset.cases:
        if existing.get("id") == case.id:
            return False

    dataset.cases.append(asdict(case))

    # Update version
    parts = dataset.version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    dataset.version = ".".join(parts)

    save_dataset(dataset)
    return True


def remove_test_case(dataset_name: str, case_id: str) -> bool:
    """Remove test case from dataset."""
    dataset = load_dataset(dataset_name)
    if not dataset:
        return False

    original_count = len(dataset.cases)
    dataset.cases = [c for c in dataset.cases if c.get("id") != case_id]

    if len(dataset.cases) < original_count:
        save_dataset(dataset)
        return True
    return False


def list_datasets() -> List[Dict]:
    """List all datasets."""
    ensure_dirs()
    datasets = []

    for f in DATASETS_DIR.glob("*.json"):
        try:
            dataset = load_dataset(f.stem)
            if dataset:
                datasets.append({
                    "name": dataset.name,
                    "version": dataset.version,
                    "cases": len(dataset.cases),
                    "tags": dataset.tags,
                    "updated": dataset.updated,
                })
        except Exception:
            pass

    return datasets


def export_dataset(name: str, format: str = "json") -> str:
    """Export dataset to various formats."""
    dataset = load_dataset(name)
    if not dataset:
        return ""

    if format == "json":
        return json.dumps(asdict(dataset), indent=2)
    elif format == "jsonl":
        return "\n".join(json.dumps(c) for c in dataset.cases)
    elif format == "csv":
        lines = ["id,input,expected_output"]
        for c in dataset.cases:
            lines.append(f"{c['id']},{c['input'][:50]},{c.get('expected_output', '')[:50]}")
        return "\n".join(lines)

    return ""


def import_dataset(name: str, filepath: str, format: str = "auto") -> int:
    """Import test cases from file."""
    path = Path(filepath)
    if not path.exists():
        return 0

    content = path.read_text()

    # Auto-detect format
    if format == "auto":
        if filepath.endswith(".jsonl"):
            format = "jsonl"
        elif filepath.endswith(".csv"):
            format = "csv"
        else:
            format = "json"

    cases = []
    if format == "jsonl":
        for line in content.strip().split("\n"):
            if line:
                cases.append(json.loads(line))
    elif format == "json":
        data = json.loads(content)
        if isinstance(data, list):
            cases = data
        elif "cases" in data:
            cases = data["cases"]

    # Add cases to dataset
    dataset = load_dataset(name)
    if not dataset:
        dataset = create_dataset(name)

    added = 0
    for c in cases:
        if "id" not in c:
            c["id"] = f"imported_{added}"
        case = TestCase(
            id=c["id"],
            input=c.get("input", ""),
            expected_output=c.get("expected_output"),
            expected_contains=c.get("expected_contains"),
            expected_not_contains=c.get("expected_not_contains"),
            tags=c.get("tags"),
            metadata=c.get("metadata"),
        )
        if add_test_case(name, case):
            added += 1

    return added


def run_dataset(name: str) -> Dict:
    """Run all test cases in dataset (mock evaluation)."""
    dataset = load_dataset(name)
    if not dataset:
        return {"error": "Dataset not found"}

    results = {
        "dataset": name,
        "version": dataset.version,
        "timestamp": datetime.now().isoformat(),
        "total": len(dataset.cases),
        "passed": 0,
        "failed": 0,
        "results": [],
    }

    for case in dataset.cases:
        # Mock evaluation - in production would call LLM
        result = {
            "id": case["id"],
            "passed": True,  # Mock
            "output": "Mock output",
        }

        # Simple check if expected_contains provided
        if case.get("expected_contains"):
            result["passed"] = True  # Would check actual output

        results["results"].append(result)
        if result["passed"]:
            results["passed"] += 1
        else:
            results["failed"] += 1

    results["pass_rate"] = f"{(results['passed']/results['total']*100):.1f}%" if results["total"] > 0 else "N/A"

    return results


def print_datasets(datasets: List[Dict]):
    """Print dataset list."""
    print("\n" + "="*60)
    print("EVALUATION DATASETS")
    print("="*60)

    if not datasets:
        print("\nNo datasets found. Create one with --create")
        return

    for ds in datasets:
        print(f"\n  {ds['name']} (v{ds['version']})")
        print(f"    Cases: {ds['cases']}")
        print(f"    Tags: {ds['tags']}")
        print(f"    Updated: {ds['updated'][:10]}")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="Evaluation Dataset Manager")
    parser.add_argument("--list", "-l", action="store_true", help="List datasets")
    parser.add_argument("--create", "-c", help="Create new dataset")
    parser.add_argument("--description", "-d", help="Dataset description")
    parser.add_argument("--add", "-a", help="Dataset to add case to")
    parser.add_argument("--case", help="Test case JSON file")
    parser.add_argument("--remove", help="Remove case by ID")
    parser.add_argument("--from-dataset", help="Target dataset for remove")
    parser.add_argument("--export", "-e", help="Export dataset")
    parser.add_argument("--format", "-f", default="json", help="Export format")
    parser.add_argument("--import-file", "-i", help="Import cases from file")
    parser.add_argument("--to-dataset", help="Target dataset for import")
    parser.add_argument("--run", "-r", help="Run dataset tests")
    parser.add_argument("--show", "-s", help="Show dataset details")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.list:
        datasets = list_datasets()
        if args.json:
            print(json.dumps(datasets, indent=2))
        else:
            print_datasets(datasets)
        return 0

    if args.create:
        dataset = create_dataset(args.create, args.description or "")
        print(f"Created dataset: {dataset.name}")
        return 0

    if args.add and args.case:
        case_data = json.loads(Path(args.case).read_text())
        case = TestCase(**case_data)
        if add_test_case(args.add, case):
            print(f"Added case {case.id} to {args.add}")
        else:
            print(f"Failed to add case")
        return 0

    if args.remove and args.from_dataset:
        if remove_test_case(args.from_dataset, args.remove):
            print(f"Removed case {args.remove}")
        else:
            print(f"Case not found")
        return 0

    if args.export:
        output = export_dataset(args.export, args.format)
        print(output)
        return 0

    if args.import_file and args.to_dataset:
        added = import_dataset(args.to_dataset, args.import_file)
        print(f"Imported {added} cases to {args.to_dataset}")
        return 0

    if args.run:
        results = run_dataset(args.run)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\nDataset: {results['dataset']}")
            print(f"Pass Rate: {results['pass_rate']}")
        return 0

    if args.show:
        dataset = load_dataset(args.show)
        if dataset:
            if args.json:
                print(json.dumps(asdict(dataset), indent=2))
            else:
                print(f"\nDataset: {dataset.name}")
                print(f"Version: {dataset.version}")
                print(f"Cases: {len(dataset.cases)}")
                print(f"Hash: {dataset.hash}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
