#!/usr/bin/env python3
"""
LangGraph Workflow Template (GAP-ORCH-002)

Template for building LangGraph-based stateful agent workflows.
Implements graph-based control flow with state management.

Usage:
    1. Copy this template to your project
    2. Define your nodes and edges
    3. Configure state schema
    4. Run the workflow

Requirements:
    pip install langgraph langchain-anthropic
"""

from typing import TypedDict, Annotated, Sequence, Literal, Optional
from datetime import datetime
import json

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolNode
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
    from langchain.tools import tool
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("LangGraph not installed. Install with: pip install langgraph langchain-anthropic")


# =============================================================================
# STATE DEFINITIONS
# =============================================================================

class AgentState(TypedDict):
    """
    State schema for the agent workflow.

    Attributes:
        messages: Conversation history
        next_action: Routing decision
        context: Additional context data
        iteration: Current iteration count
        max_iterations: Maximum allowed iterations
    """
    messages: Sequence[BaseMessage]
    next_action: Optional[str]
    context: dict
    iteration: int
    max_iterations: int


# =============================================================================
# TOOLS
# =============================================================================

if LANGGRAPH_AVAILABLE:
    @tool
    def analyze_input(text: str) -> str:
        """Analyze user input for intent and safety."""
        # Safety check
        dangerous_patterns = ["rm -rf", "sudo", "DELETE FROM", "DROP TABLE"]
        for pattern in dangerous_patterns:
            if pattern.lower() in text.lower():
                return f"SAFETY_ALERT: Potentially dangerous pattern detected: {pattern}"

        # Basic intent detection
        if any(word in text.lower() for word in ["create", "write", "make", "generate"]):
            return "INTENT: creation_task"
        elif any(word in text.lower() for word in ["find", "search", "look", "get"]):
            return "INTENT: retrieval_task"
        elif any(word in text.lower() for word in ["update", "change", "modify", "edit"]):
            return "INTENT: modification_task"
        else:
            return "INTENT: general_query"

    @tool
    def execute_task(task_description: str) -> str:
        """Execute a task based on description."""
        return f"Task executed: {task_description}\nStatus: Completed (mock)"

    @tool
    def validate_output(output: str) -> str:
        """Validate task output for correctness."""
        if len(output) < 10:
            return "VALIDATION: Output too short, may be incomplete"
        return "VALIDATION: Output appears valid"


# =============================================================================
# NODE FUNCTIONS
# =============================================================================

def create_model():
    """Create the Claude model instance."""
    if not LANGGRAPH_AVAILABLE:
        return None

    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0.7,
    )


def router_node(state: AgentState) -> AgentState:
    """
    Router node - decides next action based on state.

    This is the decision point in the graph.
    """
    messages = state["messages"]
    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations", 5)

    # Check iteration limit
    if iteration >= max_iter:
        return {
            **state,
            "next_action": "end",
            "context": {**state.get("context", {}), "reason": "max_iterations_reached"}
        }

    # Get last message
    if not messages:
        return {**state, "next_action": "end"}

    last_message = messages[-1]

    # Simple routing logic
    if isinstance(last_message, HumanMessage):
        return {**state, "next_action": "analyze", "iteration": iteration + 1}
    elif isinstance(last_message, AIMessage):
        # Check if task is complete
        if "complete" in str(last_message.content).lower():
            return {**state, "next_action": "validate"}
        return {**state, "next_action": "execute", "iteration": iteration + 1}
    else:
        return {**state, "next_action": "end"}


def analyze_node(state: AgentState) -> AgentState:
    """
    Analyze node - processes user input.
    """
    model = create_model()
    if not model:
        return state

    messages = state["messages"]

    # Add system message for analysis
    system_msg = SystemMessage(content="""
    Analyze the user's request and determine:
    1. What task they want to accomplish
    2. What information is needed
    3. What actions should be taken

    Respond with a brief analysis.
    """)

    response = model.invoke([system_msg] + list(messages))

    return {
        **state,
        "messages": list(messages) + [response],
        "next_action": "execute",
    }


def execute_node(state: AgentState) -> AgentState:
    """
    Execute node - performs the main task.
    """
    model = create_model()
    if not model:
        return state

    messages = state["messages"]

    # Add system message for execution
    system_msg = SystemMessage(content="""
    Based on the analysis, execute the requested task.
    Be thorough and provide complete results.
    End your response with "Task complete." when finished.
    """)

    response = model.invoke([system_msg] + list(messages))

    return {
        **state,
        "messages": list(messages) + [response],
        "next_action": "router",
    }


def validate_node(state: AgentState) -> AgentState:
    """
    Validate node - checks output quality.
    """
    messages = state["messages"]
    context = state.get("context", {})

    # Simple validation
    if messages:
        last_response = str(messages[-1].content)
        context["validation"] = {
            "length": len(last_response),
            "has_content": len(last_response) > 50,
            "timestamp": datetime.now().isoformat(),
        }

    return {
        **state,
        "context": context,
        "next_action": "end",
    }


def should_continue(state: AgentState) -> Literal["analyze", "execute", "validate", "end"]:
    """Determine which node to go to next."""
    return state.get("next_action", "end")


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

def create_workflow() -> Optional[StateGraph]:
    """
    Create the LangGraph workflow.

    Returns:
        Compiled StateGraph or None if LangGraph not available
    """
    if not LANGGRAPH_AVAILABLE:
        return None

    # Create graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("validate", validate_node)

    # Set entry point
    workflow.set_entry_point("router")

    # Add conditional edges from router
    workflow.add_conditional_edges(
        "router",
        should_continue,
        {
            "analyze": "analyze",
            "execute": "execute",
            "validate": "validate",
            "end": END,
        }
    )

    # Add edges back to router
    workflow.add_edge("analyze", "router")
    workflow.add_edge("execute", "router")
    workflow.add_edge("validate", END)

    # Compile
    return workflow.compile()


# =============================================================================
# WORKFLOW RUNNER
# =============================================================================

class WorkflowRunner:
    """
    High-level wrapper for running LangGraph workflows.

    Example:
        runner = WorkflowRunner()
        result = runner.run("Create a Python function to calculate factorial")
        print(result)
    """

    def __init__(self):
        self.workflow = create_workflow()
        self.execution_history = []

    def run(
        self,
        user_input: str,
        max_iterations: int = 5,
        context: dict = None,
    ) -> dict:
        """
        Run the workflow with user input.

        Args:
            user_input: The user's request
            max_iterations: Maximum workflow iterations
            context: Additional context data

        Returns:
            Final state dictionary
        """
        if not self.workflow:
            return {"error": "Workflow not initialized - LangGraph not available"}

        initial_state: AgentState = {
            "messages": [HumanMessage(content=user_input)],
            "next_action": None,
            "context": context or {},
            "iteration": 0,
            "max_iterations": max_iterations,
        }

        try:
            # Run workflow
            final_state = self.workflow.invoke(initial_state)

            # Log execution
            self.execution_history.append({
                "timestamp": datetime.now().isoformat(),
                "input": user_input,
                "iterations": final_state.get("iteration", 0),
                "context": final_state.get("context", {}),
            })

            return final_state

        except Exception as e:
            return {"error": str(e)}

    def get_response(self, user_input: str) -> str:
        """
        Run workflow and return just the final response.
        """
        result = self.run(user_input)

        if "error" in result:
            return f"Error: {result['error']}"

        messages = result.get("messages", [])
        if messages:
            # Get last AI message
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    return str(msg.content)

        return "No response generated"


# =============================================================================
# EXAMPLE PATTERNS
# =============================================================================

def create_research_workflow():
    """
    Example: Research workflow pattern.

    Graph structure:
    START -> gather_info -> analyze -> synthesize -> validate -> END
    """
    if not LANGGRAPH_AVAILABLE:
        return None

    def gather_info(state):
        # Gather information from sources
        return {**state, "next_action": "analyze"}

    def analyze_info(state):
        # Analyze gathered information
        return {**state, "next_action": "synthesize"}

    def synthesize(state):
        # Synthesize findings
        return {**state, "next_action": "validate"}

    def validate_research(state):
        # Validate research quality
        return {**state, "next_action": "end"}

    workflow = StateGraph(AgentState)
    workflow.add_node("gather", gather_info)
    workflow.add_node("analyze", analyze_info)
    workflow.add_node("synthesize", synthesize)
    workflow.add_node("validate", validate_research)

    workflow.set_entry_point("gather")
    workflow.add_edge("gather", "analyze")
    workflow.add_edge("analyze", "synthesize")
    workflow.add_edge("synthesize", "validate")
    workflow.add_edge("validate", END)

    return workflow.compile()


def create_review_workflow():
    """
    Example: Code review workflow with loops.

    Graph structure:
    START -> initial_review -> [issues_found?] -> fix -> re_review -> END
    """
    if not LANGGRAPH_AVAILABLE:
        return None

    class ReviewState(TypedDict):
        code: str
        issues: list
        fixed: bool
        review_count: int

    def initial_review(state):
        # Perform initial review
        issues = ["Issue 1", "Issue 2"]  # Mock issues
        return {**state, "issues": issues, "review_count": 1}

    def fix_issues(state):
        # Fix identified issues
        return {**state, "fixed": True}

    def re_review(state):
        # Re-review after fixes
        return {**state, "issues": [], "review_count": state["review_count"] + 1}

    def should_fix(state):
        if state.get("issues") and state.get("review_count", 0) < 3:
            return "fix"
        return "end"

    workflow = StateGraph(ReviewState)
    workflow.add_node("review", initial_review)
    workflow.add_node("fix", fix_issues)
    workflow.add_node("re_review", re_review)

    workflow.set_entry_point("review")
    workflow.add_conditional_edges("review", should_fix, {"fix": "fix", "end": END})
    workflow.add_edge("fix", "re_review")
    workflow.add_conditional_edges("re_review", should_fix, {"fix": "fix", "end": END})

    return workflow.compile()


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

def example_usage():
    """Demonstrate workflow usage."""
    print("=" * 60)
    print("LangGraph Workflow Template")
    print("=" * 60)

    if not LANGGRAPH_AVAILABLE:
        print("\nLangGraph not installed. This is a template file.")
        print("Install with: pip install langgraph langchain-anthropic")
        return

    # Create and run workflow
    runner = WorkflowRunner()

    examples = [
        "Calculate the sum of numbers from 1 to 100",
        "Explain how recursion works in Python",
    ]

    for query in examples:
        print(f"\n> {query}")
        response = runner.get_response(query)
        print(f"< {response[:200]}..." if len(response) > 200 else f"< {response}")


if __name__ == "__main__":
    example_usage()
