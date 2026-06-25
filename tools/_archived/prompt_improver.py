#!/usr/bin/env python3
"""
Prompt Improvement Protocol (GAP-OP-019)

Analyze prompt effectiveness and suggest improvements based on best practices.

Usage:
    python prompt_improver.py --analyze "Your prompt here"
    python prompt_improver.py --file prompt.txt --verbose
    python prompt_improver.py --compare prompt1.txt prompt2.txt
    python prompt_improver.py --score prompt.txt

Features:
- Quality scoring (0-100)
- Issue detection (length, clarity, structure)
- Concrete improvement suggestions
- Prompt comparison
"""

import argparse
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any


# Quality metrics thresholds
MIN_LENGTH = 10  # Too short
IDEAL_MIN_LENGTH = 50  # Good minimum
MAX_LENGTH = 2000  # Too verbose
IDEAL_MAX_LENGTH = 1000  # Good maximum


def analyze_prompt(prompt: str) -> Dict[str, Any]:
    """
    Analyze prompt and return quality metrics.

    Args:
        prompt: The prompt text to analyze

    Returns:
        Dictionary with score, issues, and suggestions
    """
    issues = []
    suggestions = []
    score = 100.0

    # Check 1: Length
    length = len(prompt)
    if length < MIN_LENGTH:
        issues.append("Prompt too short (< 10 chars)")
        suggestions.append("Add more context: What is the task? What format do you expect?")
        score -= 30

    elif length < IDEAL_MIN_LENGTH:
        issues.append("Prompt could be more detailed")
        suggestions.append("Add context about the task, expected output format, and constraints")
        score -= 10

    if length > MAX_LENGTH:
        issues.append("Prompt too long (> 2000 chars)")
        suggestions.append("Split into sections: Task, Context, Constraints, Expected Output")
        score -= 15

    # Check 2: Structure
    has_sections = bool(re.search(r'\n\n', prompt))  # Paragraph breaks
    has_bullets = bool(re.search(r'[\n\r]\s*[-*•]\s', prompt))  # Bullet points
    has_numbers = bool(re.search(r'[\n\r]\s*\d+[.)]\s', prompt))  # Numbered lists

    if not (has_sections or has_bullets or has_numbers) and length > 100:
        issues.append("Lacks structure (no sections, bullets, or lists)")
        suggestions.append("Use sections or bullet points to organize information")
        score -= 15

    # Check 3: Clarity
    # Check for vague words
    vague_words = ['help', 'thing', 'stuff', 'something', 'whatever', 'etc']
    vague_count = sum(prompt.lower().count(word) for word in vague_words)
    if vague_count > 0:
        issues.append(f"Contains vague language ({vague_count} occurrences)")
        suggestions.append("Replace vague terms with specific details")
        score -= min(vague_count * 10, 30)

    # Check 4: Specificity
    has_examples = bool(re.search(r'(example|e\.g\.|for instance)', prompt, re.IGNORECASE))
    has_format = bool(re.search(r'(format|output|return|provide)', prompt, re.IGNORECASE))
    has_constraints = bool(re.search(r'(must|should|don\'t|avoid|only|exactly)', prompt, re.IGNORECASE))

    specificity_score = sum([has_examples, has_format, has_constraints])
    if specificity_score == 0 and length > 50:
        issues.append("Lacks specificity (no examples, format, or constraints)")
        suggestions.append("Add: 1) Example of expected output, 2) Format requirements, 3) Constraints")
        score -= 20
    elif specificity_score == 1:
        suggestions.append("Consider adding more specificity: examples, format details, or constraints")
        score -= 5

    # Check 5: Role clarity
    has_role = bool(re.search(r'(you are|act as|as a)', prompt, re.IGNORECASE))
    if not has_role and length > 50:
        suggestions.append("Consider defining a role: 'You are a [expert type]...'")
        score -= 5

    # Check 6: Task clarity
    has_task = bool(re.search(r'(task|goal|objective|need|want|please)', prompt, re.IGNORECASE))
    if not has_task and length > 20:
        issues.append("Task not clearly stated")
        suggestions.append("Explicitly state: 'Task: [what you need]'")
        score -= 15

    # Check 7: Context
    has_context = bool(re.search(r'(context|background|because|for|in order to)', prompt, re.IGNORECASE))
    if not has_context and length > 100:
        suggestions.append("Add context: Why is this task needed? What's the background?")
        score -= 5

    # Ensure score is in bounds
    score = max(0, min(100, score))

    return {
        'score': round(score, 1),
        'issues': issues,
        'suggestions': suggestions,
        'metrics': {
            'length': length,
            'has_structure': has_sections or has_bullets or has_numbers,
            'has_role': has_role,
            'has_task': has_task,
            'has_examples': has_examples,
            'has_format': has_format,
            'has_constraints': has_constraints,
            'has_context': has_context,
            'vague_count': vague_count
        }
    }


def compare_prompts(prompt1: str, prompt2: str) -> Dict[str, Any]:
    """
    Compare two prompts.

    Args:
        prompt1: First prompt
        prompt2: Second prompt

    Returns:
        Comparison results with scores and winner
    """
    result1 = analyze_prompt(prompt1)
    result2 = analyze_prompt(prompt2)

    winner = 'prompt1' if result1['score'] > result2['score'] else 'prompt2'
    if result1['score'] == result2['score']:
        winner = 'tie'

    return {
        'prompt1_score': result1['score'],
        'prompt2_score': result2['score'],
        'winner': winner,
        'prompt1_issues': len(result1['issues']),
        'prompt2_issues': len(result2['issues']),
        'improvement': abs(result1['score'] - result2['score'])
    }


def format_report(analysis: Dict[str, Any], verbose: bool = False) -> str:
    """Format analysis results as readable report."""
    report = []
    report.append("=" * 60)
    report.append("PROMPT QUALITY ANALYSIS")
    report.append("=" * 60)
    report.append(f"\nOverall Score: {analysis['score']}/100")

    # Score interpretation
    score = analysis['score']
    if score >= 80:
        report.append("Quality: EXCELLENT ✓")
    elif score >= 60:
        report.append("Quality: GOOD")
    elif score >= 40:
        report.append("Quality: FAIR")
    else:
        report.append("Quality: POOR")

    # Issues
    if analysis['issues']:
        report.append(f"\n{len(analysis['issues'])} Issues Found:")
        for i, issue in enumerate(analysis['issues'], 1):
            report.append(f"  {i}. {issue}")
    else:
        report.append("\nNo critical issues found ✓")

    # Suggestions
    if analysis['suggestions']:
        report.append(f"\n{len(analysis['suggestions'])} Suggestions:")
        for i, suggestion in enumerate(analysis['suggestions'], 1):
            report.append(f"  {i}. {suggestion}")

    # Verbose metrics
    if verbose and analysis.get('metrics'):
        report.append("\nDetailed Metrics:")
        metrics = analysis['metrics']
        report.append(f"  Length: {metrics['length']} chars")
        report.append(f"  Has structure: {'Yes ✓' if metrics['has_structure'] else 'No'}")
        report.append(f"  Has role: {'Yes ✓' if metrics['has_role'] else 'No'}")
        report.append(f"  Has task: {'Yes ✓' if metrics['has_task'] else 'No'}")
        report.append(f"  Has examples: {'Yes ✓' if metrics['has_examples'] else 'No'}")
        report.append(f"  Has format spec: {'Yes ✓' if metrics['has_format'] else 'No'}")
        report.append(f"  Has constraints: {'Yes ✓' if metrics['has_constraints'] else 'No'}")
        report.append(f"  Has context: {'Yes ✓' if metrics['has_context'] else 'No'}")
        report.append(f"  Vague terms: {metrics['vague_count']}")

    report.append("=" * 60)
    return "\n".join(report)


def main():
    """CLI interface."""
    parser = argparse.ArgumentParser(
        description='Analyze and improve prompt quality',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze prompt from text
  %(prog)s --analyze "You are a coding assistant. Help me write Python."

  # Analyze prompt from file
  %(prog)s --file prompt.txt --verbose

  # Compare two prompts
  %(prog)s --compare prompt1.txt prompt2.txt

  # Get just the score
  %(prog)s --score prompt.txt
        """
    )

    parser.add_argument('--analyze', type=str, help='Analyze prompt text')
    parser.add_argument('--file', type=Path, help='Analyze prompt from file')
    parser.add_argument('--compare', nargs=2, type=Path, help='Compare two prompt files')
    parser.add_argument('--score', type=Path, help='Show only score for file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed metrics')
    parser.add_argument('--json', action='store_true', help='Output JSON format')

    args = parser.parse_args()

    # Input validation
    if not any([args.analyze, args.file, args.compare, args.score]):
        parser.print_help()
        return 1

    try:
        # Compare mode
        if args.compare:
            prompt1 = args.compare[0].read_text()
            prompt2 = args.compare[1].read_text()
            result = compare_prompts(prompt1, prompt2)

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print("=" * 60)
                print("PROMPT COMPARISON")
                print("=" * 60)
                print(f"\nPrompt 1 ({args.compare[0].name}): {result['prompt1_score']}/100")
                print(f"Prompt 2 ({args.compare[1].name}): {result['prompt2_score']}/100")
                print(f"\nWinner: {result['winner'].upper()}")
                print(f"Improvement: {result['improvement']:.1f} points")
                print("=" * 60)

        # Score only mode
        elif args.score:
            prompt = args.score.read_text()
            result = analyze_prompt(prompt)
            print(result['score'])

        # Analyze mode
        else:
            if args.analyze:
                prompt = args.analyze
            else:
                prompt = args.file.read_text()

            result = analyze_prompt(prompt)

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(format_report(result, verbose=args.verbose))

        return 0

    except FileNotFoundError as e:
        print(f"Error: File not found - {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
