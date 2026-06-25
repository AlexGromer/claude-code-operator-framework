#!/usr/bin/env python3
"""
User Context Detector (GAP-OP-021)

Detect user experience level and domain expertise from conversation patterns.
Adjust response verbosity recommendations accordingly.

Usage:
    python user_context_detector.py --analyze session.jsonl
    python user_context_detector.py --profile --messages "msg1" "msg2" "msg3"
    python user_context_detector.py --recommend session.jsonl

Features:
- Experience level detection (beginner/intermediate/expert)
- Domain expertise detection (security, devops, etc.)
- Verbosity recommendation
- Confidence scoring
"""

import argparse
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter


# Keyword patterns for experience detection
BEGINNER_PATTERNS = [
    r'\b(how do i|what is|i don\'t understand|i\'m new|help me|confused|beginner)\b',
    r'\b(tutorial|guide|learn|teach me|explain|step by step)\b',
    r'\b(simple|basic|easy|start|getting started)\b',
]

EXPERT_PATTERNS = [
    r'\b(optimize|refactor|architecture|design pattern|performance)\b',
    r'\b(implement|algorithm|complexity|O\(|scalability|distributed)\b',
    r'\b(kubernetes|terraform|ansible|docker-compose|helm|argocd)\b',
    r'\b(nmap|burp|metasploit|ghidra|ida|radare2)\b',
    r'\b(zero-downtime|blue-green|canary|circuit breaker|saga)\b',
    r'\b(SOLID|DRY|KISS|YAGNI|microservices|event-driven)\b',
]

# Domain keyword patterns
DOMAIN_PATTERNS = {
    'security': [
        r'\b(pentest|vulnerability|exploit|CVE|injection|XSS|CSRF)\b',
        r'\b(nmap|burp|nuclei|sqlmap|metasploit|owasp)\b',
        r'\b(firewall|WAF|IDS|IPS|SIEM|SOC)\b',
    ],
    'devops': [
        r'\b(deploy|pipeline|CI/CD|infrastructure|kubernetes|docker)\b',
        r'\b(terraform|ansible|helm|jenkins|gitlab|argocd)\b',
        r'\b(monitoring|observability|prometheus|grafana|logging)\b',
    ],
    'development': [
        r'\b(code|function|class|algorithm|debug|refactor)\b',
        r'\b(python|javascript|go|rust|java|typescript)\b',
        r'\b(test|unit test|integration|coverage|TDD)\b',
    ],
    'data': [
        r'\b(database|SQL|postgres|mysql|mongodb|redis)\b',
        r'\b(data|dataset|analytics|ETL|pipeline)\b',
        r'\b(pandas|numpy|scikit|tensorflow|pytorch)\b',
    ],
}


def detect_experience(messages: List[str]) -> Dict[str, Any]:
    """
    Detect user experience level from messages.

    Args:
        messages: List of user messages

    Returns:
        Dictionary with level, confidence, and evidence
    """
    if not messages:
        return {
            'level': 'intermediate',
            'confidence': 0,
            'evidence': []
        }

    # Combine all messages
    text = ' '.join(messages).lower()

    # Count pattern matches
    beginner_score = 0
    expert_score = 0
    evidence = []

    for pattern in BEGINNER_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            beginner_score += len(matches)
            evidence.append(f"Beginner indicator: {matches[0]}")

    for pattern in EXPERT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            expert_score += len(matches)
            evidence.append(f"Expert indicator: {matches[0]}")

    # Determine level
    total_score = beginner_score + expert_score
    if total_score == 0:
        level = 'intermediate'
        confidence = 30
    elif beginner_score > expert_score * 2:
        level = 'beginner'
        confidence = min(100, (beginner_score / (total_score + 1)) * 100)
    elif expert_score > beginner_score * 2:
        level = 'expert'
        confidence = min(100, (expert_score / (total_score + 1)) * 100)
    else:
        level = 'intermediate'
        confidence = 50

    # Adjust confidence based on message count
    if len(messages) < 3:
        confidence *= 0.7  # Lower confidence with few messages

    return {
        'level': level,
        'confidence': round(confidence, 1),
        'evidence': evidence[:5],  # Top 5 evidence items
        'beginner_score': beginner_score,
        'expert_score': expert_score,
        'message_count': len(messages)
    }


def detect_domains(messages: List[str]) -> Dict[str, Any]:
    """
    Detect domain expertise from messages.

    Args:
        messages: List of user messages

    Returns:
        Dictionary with detected domains and confidence
    """
    if not messages:
        return {'domains': [], 'confidence': 0}

    text = ' '.join(messages).lower()

    domain_scores = {}
    for domain, patterns in DOMAIN_PATTERNS.items():
        score = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            score += len(matches)

        if score > 0:
            domain_scores[domain] = score

    # Sort by score
    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)

    # Calculate confidence
    if sorted_domains:
        top_score = sorted_domains[0][1]
        confidence = min(100, top_score * 15)  # Scale score to confidence
    else:
        confidence = 0

    return {
        'domains': [d[0] for d in sorted_domains],
        'scores': dict(sorted_domains),
        'confidence': round(confidence, 1)
    }


def recommend_verbosity(messages: List[str]) -> Dict[str, Any]:
    """
    Recommend response verbosity level.

    Args:
        messages: List of user messages

    Returns:
        Dictionary with verbosity recommendation
    """
    experience = detect_experience(messages)
    level = experience['level']

    # Map experience to verbosity
    verbosity_map = {
        'beginner': 'high',
        'intermediate': 'medium',
        'expert': 'low'
    }

    verbosity = verbosity_map.get(level, 'medium')

    # Provide specific recommendations
    recommendations = {
        'high': [
            'Explain technical terms',
            'Provide step-by-step instructions',
            'Include examples for each concept',
            'Use simple language'
        ],
        'medium': [
            'Balance explanation with efficiency',
            'Define uncommon terms',
            'Provide examples for complex concepts'
        ],
        'low': [
            'Be concise and direct',
            'Assume technical knowledge',
            'Skip basic explanations',
            'Focus on specifics'
        ]
    }

    return {
        'verbosity': verbosity,
        'experience_level': level,
        'recommendations': recommendations[verbosity],
        'confidence': experience['confidence']
    }


def analyze_session_file(file_path: Path) -> List[str]:
    """
    Extract messages from session JSONL file.

    Args:
        file_path: Path to session file

    Returns:
        List of user messages
    """
    messages = []

    try:
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        # Extract user messages (format may vary)
                        if isinstance(data, dict):
                            if 'message' in data and data.get('role') == 'user':
                                messages.append(data['message'])
                            elif 'content' in data and data.get('role') == 'user':
                                messages.append(data['content'])
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"Warning: Error reading file - {e}", file=sys.stderr)

    return messages


def format_profile(experience: Dict, domains: Dict, verbosity: Dict) -> str:
    """Format user profile report."""
    report = []
    report.append("=" * 60)
    report.append("USER CONTEXT PROFILE")
    report.append("=" * 60)

    # Experience level
    report.append(f"\nExperience Level: {experience['level'].upper()}")
    report.append(f"Confidence: {experience['confidence']:.1f}%")

    if experience.get('evidence'):
        report.append("\nEvidence:")
        for ev in experience['evidence'][:3]:
            report.append(f"  • {ev}")

    # Domain expertise
    if domains['domains']:
        report.append(f"\nDomain Expertise: {', '.join(domains['domains'])}")
        report.append(f"Confidence: {domains['confidence']:.1f}%")
    else:
        report.append("\nDomain Expertise: Not detected")

    # Verbosity recommendation
    report.append(f"\nRecommended Verbosity: {verbosity['verbosity'].upper()}")
    report.append("\nGuidelines:")
    for rec in verbosity['recommendations']:
        report.append(f"  • {rec}")

    # Stats
    report.append(f"\nAnalyzed {experience.get('message_count', 0)} messages")

    report.append("=" * 60)
    return "\n".join(report)


def main():
    """CLI interface."""
    parser = argparse.ArgumentParser(
        description='Detect user context and experience level',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze session file
  %(prog)s --analyze session.jsonl

  # Generate user profile
  %(prog)s --profile --messages "how do I use git?" "what is kubernetes?"

  # Get verbosity recommendation
  %(prog)s --recommend session.jsonl
        """
    )

    parser.add_argument('--analyze', type=Path, help='Analyze session file')
    parser.add_argument('--profile', action='store_true', help='Generate full profile')
    parser.add_argument('--recommend', type=Path, help='Get verbosity recommendation')
    parser.add_argument('--messages', nargs='+', help='Analyze provided messages')
    parser.add_argument('--json', action='store_true', help='Output JSON format')

    args = parser.parse_args()

    # Input validation
    if not any([args.analyze, args.profile, args.recommend, args.messages]):
        parser.print_help()
        return 1

    try:
        # Get messages
        messages = []
        if args.analyze or args.recommend:
            file_path = args.analyze or args.recommend
            messages = analyze_session_file(file_path)
            if not messages:
                print(f"Warning: No messages found in {file_path}", file=sys.stderr)
        elif args.messages:
            messages = args.messages

        # Profile mode
        if args.profile or args.analyze:
            experience = detect_experience(messages)
            domains = detect_domains(messages)
            verbosity = recommend_verbosity(messages)

            if args.json:
                result = {
                    'experience': experience,
                    'domains': domains,
                    'verbosity': verbosity
                }
                print(json.dumps(result, indent=2))
            else:
                print(format_profile(experience, domains, verbosity))

        # Recommend mode
        elif args.recommend:
            verbosity = recommend_verbosity(messages)

            if args.json:
                print(json.dumps(verbosity, indent=2))
            else:
                print(f"Recommended verbosity: {verbosity['verbosity']}")
                print(f"Based on: {verbosity['experience_level']} level")
                print(f"Confidence: {verbosity['confidence']:.1f}%")

        return 0

    except FileNotFoundError as e:
        print(f"Error: File not found - {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
