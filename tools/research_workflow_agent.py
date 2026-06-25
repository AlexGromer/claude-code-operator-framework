#!/usr/bin/env python3
"""
Research Workflow Agent - Interactive Protocol Assistant
Guides user through research-to-practice workflow with agent assistance.

Workflow:
1. Check for new digest
2. Display CRITICAL/HIGH items
3. Offer to score discoveries
4. Suggest gap creation
5. Recommend PoC testing

Usage:
    python research_workflow_agent.py

Version: 1.0.0
Created: 2026-01-27
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

DIGEST_DIR = Path.home() / ".claude" / "evaluation" / "data" / "research_digests"
GAPS_FILE = Path.home() / ".claude" / "GAPS.md"
TOOLS_DIR = Path.home() / ".claude" / "tools"

class ResearchWorkflowAgent:
    """Interactive agent for research-to-practice workflow."""

    def __init__(self):
        self.latest_digest = self.get_latest_digest()
        self.discoveries = []

    def get_latest_digest(self):
        """Get the most recent digest file."""
        if not DIGEST_DIR.exists():
            return None

        digests = sorted(DIGEST_DIR.glob("digest_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        return digests[0] if digests else None

    def parse_digest(self):
        """Parse digest and extract CRITICAL/HIGH discoveries."""
        if not self.latest_digest:
            return []

        content = self.latest_digest.read_text()
        discoveries = []
        current_priority = None
        current_category = None

        for line in content.split('\n'):
            # Detect priority sections
            if '## 🔴 CRITICAL Priority' in line:
                current_priority = 'CRITICAL'
            elif '## 🟠 HIGH Priority' in line:
                current_priority = 'HIGH'
            elif line.startswith('## ') and '🟡' in line:
                # Stop at MEDIUM priority
                break

            # Detect category
            if line.startswith('### ') and current_priority:
                current_category = line.replace('### ', '').strip()

            # Extract discovery
            if line.startswith('- **') and current_priority:
                title = line.split('**')[1]
                discovery = {
                    'title': title,
                    'priority': current_priority,
                    'category': current_category,
                    'link': None,
                    'github_url': None,
                    'arxiv_id': None
                }
                discoveries.append(discovery)
            elif discoveries and line.strip().startswith('- 🔗 ['):
                # Extract link
                discoveries[-1]['link'] = line.split('](')[1].split(')')[0] if '](http' in line else None
                # Check if GitHub URL
                if discoveries[-1]['link'] and 'github.com' in discoveries[-1]['link']:
                    discoveries[-1]['github_url'] = discoveries[-1]['link']
                # Check if arXiv
                if discoveries[-1]['link'] and 'arxiv.org/abs/' in discoveries[-1]['link']:
                    arxiv_id = discoveries[-1]['link'].split('arxiv.org/abs/')[-1]
                    discoveries[-1]['arxiv_id'] = arxiv_id

        return discoveries

    def display_summary(self):
        """Display digest summary."""
        print("\n" + "="*80)
        print("📊 RESEARCH DIGEST WORKFLOW")
        print("="*80)
        print(f"")
        print(f"📅 Digest: {self.latest_digest.name.replace('digest_', '').replace('.md', '')}")
        print(f"📂 Location: {self.latest_digest}")
        print(f"")

        if not self.discoveries:
            print("✅ No CRITICAL/HIGH priority items found.")
            print("")
            return False

        critical_count = sum(1 for d in self.discoveries if d['priority'] == 'CRITICAL')
        high_count = sum(1 for d in self.discoveries if d['priority'] == 'HIGH')

        print(f"🔴 CRITICAL items: {critical_count}")
        print(f"🟠 HIGH items: {high_count}")
        print(f"")
        print("="*80)
        print("")

        return True

    def display_discoveries(self, limit=10):
        """Display top discoveries."""
        print(f"Top {min(limit, len(self.discoveries))} discoveries:\n")

        for i, discovery in enumerate(self.discoveries[:limit], 1):
            icon = '🔴' if discovery['priority'] == 'CRITICAL' else '🟠'
            print(f"{i}. {icon} {discovery['title']}")
            print(f"   Category: {discovery['category']}")
            if discovery['github_url']:
                print(f"   GitHub: {discovery['github_url']}")
            if discovery['arxiv_id']:
                print(f"   arXiv: {discovery['arxiv_id']}")
            print(f"   Link: {discovery['link']}")
            print("")

    def suggest_actions(self):
        """Suggest next actions to user."""
        print("="*80)
        print("RECOMMENDED ACTIONS")
        print("="*80)
        print("")
        print("The agent can help you with:")
        print("")
        print("1. 📊 Score discoveries (5-dimension relevance matrix)")
        print("   → Identifies P1/P2 candidates for integration")
        print("")
        print("2. 📝 Create gaps in GAPS.md")
        print("   → Tracks P1/P2 discoveries for future work")
        print("")
        print("3. 🧪 Schedule PoC testing")
        print("   → Validates high-score discoveries (6-10h per PoC)")
        print("")
        print("4. 📖 View full digest")
        print("   → Read complete report with all priorities")
        print("")
        print("="*80)
        print("")

    def generate_agent_prompt(self):
        """Generate prompt for Claude agent."""
        if not self.discoveries:
            return None

        # Select top 5 CRITICAL discoveries
        top_discoveries = [d for d in self.discoveries if d['priority'] == 'CRITICAL'][:5]

        prompt = f"""# Research Digest Review Request

Новый research digest содержит {len(self.discoveries)} CRITICAL/HIGH priority discoveries.

**Top {len(top_discoveries)} CRITICAL discoveries:**

"""

        for i, d in enumerate(top_discoveries, 1):
            prompt += f"{i}. **{d['title']}**\n"
            prompt += f"   - Category: {d['category']}\n"
            if d['github_url']:
                prompt += f"   - GitHub: {d['github_url']}\n"
            if d['arxiv_id']:
                prompt += f"   - arXiv: {d['arxiv_id']}\n"
            prompt += "\n"

        prompt += """
**Что нужно сделать:**

1. Для каждого discovery из списка выше:
   - Запусти scoring: `python ~/.claude/tools/score_discovery.py --title "..." --github-url "..." --arxiv-id "..."`
   - Покажи мне результаты (total_score, priority, recommended_action)

2. Для discoveries с total_score ≥ 60 (P1/P2):
   - Предложи создать gap в GAPS.md
   - Покажи draft gap description

3. Для discoveries с total_score ≥ 80 (P1):
   - Рекомендуй immediate PoC testing (<1 week)
   - Предложи план PoC (4-stage protocol)

**Контекст:**
- Workflow reference: ~/.claude/evaluation/research_workflow.md
- Validation framework: ~/.claude/evaluation/validation_workflow.md
- Scoring tool: ~/.claude/tools/score_discovery.py

Начинай со scoring первого discovery.
"""

        return prompt

    def run(self):
        """Run interactive workflow."""
        # Step 1: Parse digest
        self.discoveries = self.parse_digest()

        # Step 2: Display summary
        has_items = self.display_summary()

        if not has_items:
            return 0

        # Step 3: Display discoveries
        self.display_discoveries(limit=10)

        # Step 4: Suggest actions
        self.suggest_actions()

        # Step 5: Generate agent prompt
        agent_prompt = self.generate_agent_prompt()

        if agent_prompt:
            prompt_file = Path("/tmp/research_digest_prompt.md")
            prompt_file.write_text(agent_prompt)

            print(f"✅ Agent prompt generated: {prompt_file}")
            print("")
            print("NEXT STEP:")
            print("Copy the following message to Claude Code:")
            print("")
            print("-"*80)
            print(agent_prompt)
            print("-"*80)
            print("")
            print("Alternatively, in Claude Code session, say:")
            print('  "Выполни workflow из /tmp/research_digest_prompt.md"')
            print("")

        return 0


def main():
    agent = ResearchWorkflowAgent()
    return agent.run()


if __name__ == "__main__":
    sys.exit(main())
