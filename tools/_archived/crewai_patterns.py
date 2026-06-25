#!/usr/bin/env python3
"""
CrewAI Patterns Tool

Enterprise multi-agent patterns using CrewAI framework.
Addresses GAP-ORCH-003: CrewAI enterprise patterns.
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class RoleType(Enum):
    """CrewAI role types."""
    RESEARCHER = "researcher"
    WRITER = "writer"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    PLANNER = "planner"
    EXECUTOR = "executor"


class ProcessType(Enum):
    """CrewAI process types."""
    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"
    CONSENSUS = "consensus"


@dataclass
class CrewRole:
    """CrewAI role definition."""
    name: str
    role_type: RoleType
    goal: str
    backstory: str
    tools: List[str]


@dataclass
class CrewPattern:
    """CrewAI crew pattern."""
    name: str
    process: ProcessType
    agents: List[CrewRole]
    description: str
    code_example: str


# Predefined roles
PREDEFINED_ROLES: Dict[str, CrewRole] = {
    "senior_researcher": CrewRole(
        name="Senior Researcher",
        role_type=RoleType.RESEARCHER,
        goal="Conduct comprehensive research on given topics",
        backstory="Expert researcher with 10+ years experience in data analysis",
        tools=["search", "scrape", "read_file"]
    ),
    "tech_writer": CrewRole(
        name="Technical Writer",
        role_type=RoleType.WRITER,
        goal="Create clear, well-structured technical documentation",
        backstory="Professional technical writer specializing in complex topics",
        tools=["write_file", "format"]
    ),
    "code_reviewer": CrewRole(
        name="Code Reviewer",
        role_type=RoleType.REVIEWER,
        goal="Review code for quality, security, and best practices",
        backstory="Senior engineer with expertise in code quality",
        tools=["read_file", "analyze_code"]
    ),
    "project_planner": CrewRole(
        name="Project Planner",
        role_type=RoleType.PLANNER,
        goal="Create detailed project plans and task breakdowns",
        backstory="Experienced PM with agile and waterfall expertise",
        tools=["create_tasks", "estimate"]
    )
}


# Crew patterns
CREW_PATTERNS: Dict[str, CrewPattern] = {
    "research_team": CrewPattern(
        name="Research Team",
        process=ProcessType.SEQUENTIAL,
        agents=[
            PREDEFINED_ROLES["senior_researcher"],
            PREDEFINED_ROLES["tech_writer"]
        ],
        description="Research and document findings",
        code_example="""
from crewai import Agent, Task, Crew, Process

researcher = Agent(
    role="Senior Researcher",
    goal="Conduct comprehensive research",
    backstory="Expert researcher with deep expertise",
    tools=[search_tool, scrape_tool],
    llm=llm
)

writer = Agent(
    role="Technical Writer",
    goal="Create clear documentation",
    backstory="Professional technical writer",
    tools=[write_tool],
    llm=llm
)

research_task = Task(
    description="Research {topic} and compile findings",
    agent=researcher,
    expected_output="Comprehensive research report"
)

write_task = Task(
    description="Write documentation based on research",
    agent=writer,
    expected_output="Well-structured document",
    context=[research_task]
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    process=Process.sequential,
    verbose=True
)

result = crew.kickoff(inputs={"topic": "AI Safety"})
"""
    ),
    
    "code_review_crew": CrewPattern(
        name="Code Review Crew",
        process=ProcessType.HIERARCHICAL,
        agents=[
            PREDEFINED_ROLES["code_reviewer"],
            PREDEFINED_ROLES["senior_researcher"]
        ],
        description="Comprehensive code review with research",
        code_example="""
from crewai import Agent, Task, Crew, Process

reviewer = Agent(
    role="Code Reviewer",
    goal="Review code for quality and security",
    backstory="Senior engineer focused on code quality",
    tools=[analyze_tool, lint_tool],
    llm=llm
)

security_analyst = Agent(
    role="Security Analyst",
    goal="Identify security vulnerabilities",
    backstory="Security expert with OWASP expertise",
    tools=[security_scan_tool],
    llm=llm
)

manager = Agent(
    role="Review Manager",
    goal="Coordinate review process",
    backstory="Engineering manager",
    llm=llm,
    allow_delegation=True
)

crew = Crew(
    agents=[manager, reviewer, security_analyst],
    tasks=[quality_task, security_task, summary_task],
    process=Process.hierarchical,
    manager_llm=manager_llm
)
"""
    ),
    
    "content_pipeline": CrewPattern(
        name="Content Pipeline",
        process=ProcessType.SEQUENTIAL,
        agents=[
            PREDEFINED_ROLES["senior_researcher"],
            PREDEFINED_ROLES["tech_writer"],
            PREDEFINED_ROLES["code_reviewer"]
        ],
        description="End-to-end content creation pipeline",
        code_example="""
from crewai import Crew, Process
from crewai.tools import tool

@tool
def search_web(query: str) -> str:
    \"\"\"Search the web for information.\"\"\"
    # Implementation
    return results

crew = Crew(
    agents=[researcher, writer, editor],
    tasks=[
        Task(description="Research topic", agent=researcher),
        Task(description="Write draft", agent=writer),
        Task(description="Review and edit", agent=editor)
    ],
    process=Process.sequential,
    memory=True,  # Enable crew memory
    cache=True    # Enable response caching
)
"""
    )
}


# Enterprise patterns
ENTERPRISE_PATTERNS = {
    "observability": """
# CrewAI with observability
from crewai import Crew
import langfuse

# Integrate with LangFuse for tracing
crew = Crew(
    agents=[...],
    tasks=[...],
    callbacks=[langfuse_callback]
)
""",
    
    "human_in_loop": """
# Human-in-the-loop pattern
from crewai import Task

task = Task(
    description="Create marketing plan",
    agent=planner,
    human_input=True,  # Request human approval
    expected_output="Approved marketing plan"
)
""",
    
    "memory_persistence": """
# Persistent memory across sessions
from crewai import Crew
from crewai.memory import LongTermMemory

crew = Crew(
    agents=[...],
    tasks=[...],
    memory=True,
    long_term_memory=LongTermMemory(
        storage_type="json",
        path="./crew_memory.json"
    )
)
""",
    
    "async_execution": """
# Async crew execution
import asyncio
from crewai import Crew

async def run_crew():
    result = await crew.kickoff_async(inputs={"topic": "..."})
    return result

# Run multiple crews in parallel
results = await asyncio.gather(
    crew1.kickoff_async(inputs1),
    crew2.kickoff_async(inputs2)
)
"""
}


def get_crew_pattern(name: str) -> Optional[Dict[str, Any]]:
    """Get a specific crew pattern."""
    if name in CREW_PATTERNS:
        pattern = CREW_PATTERNS[name]
        return {
            "name": pattern.name,
            "process": pattern.process.value,
            "description": pattern.description,
            "agents": [{"name": a.name, "role": a.role_type.value} for a in pattern.agents],
            "code": pattern.code_example
        }
    return None


def list_patterns() -> Dict[str, List[str]]:
    """List all available patterns."""
    return {
        "crew_patterns": list(CREW_PATTERNS.keys()),
        "predefined_roles": list(PREDEFINED_ROLES.keys()),
        "enterprise_patterns": list(ENTERPRISE_PATTERNS.keys())
    }


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CrewAI Patterns")
    parser.add_argument("--list", action="store_true", help="List all patterns")
    parser.add_argument("--pattern", type=str, help="Get specific crew pattern")
    parser.add_argument("--role", type=str, help="Get predefined role")
    parser.add_argument("--enterprise", type=str, help="Get enterprise pattern")
    
    args = parser.parse_args()
    
    if args.list:
        patterns = list_patterns()
        print(json.dumps(patterns, indent=2))
    
    elif args.pattern:
        pattern = get_crew_pattern(args.pattern)
        if pattern:
            print(json.dumps(pattern, indent=2))
            print("\n--- Code Example ---")
            print(pattern["code"])
        else:
            print(f"Pattern '{args.pattern}' not found")
    
    elif args.role:
        if args.role in PREDEFINED_ROLES:
            role = PREDEFINED_ROLES[args.role]
            print(json.dumps({
                "name": role.name,
                "type": role.role_type.value,
                "goal": role.goal,
                "backstory": role.backstory,
                "tools": role.tools
            }, indent=2))
        else:
            print(f"Role '{args.role}' not found")
    
    elif args.enterprise:
        if args.enterprise in ENTERPRISE_PATTERNS:
            print(ENTERPRISE_PATTERNS[args.enterprise])
        else:
            print(f"Enterprise pattern '{args.enterprise}' not found")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
