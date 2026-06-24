"""LangGraph StateGraph for the SmartHome autonomous agent.

Dual entry points:
- monitoring_entry: timer-driven autonomous sensor loop
- user_entry: human message via Telegram/API/frontend
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import SmartHomeState
from .nodes import (
    monitoring_node,
    evaluating_node,
    critical_handler_node,
    deciding_node,
    executing_node,
    notifying_node,
    receiving_input_node,
    command_router_node,
    query_handler_node,
    direct_exec_node,
    waiting_confirmation_node,
    waiting_clarification_node,
    silenced_node,
    error_handler_node,
    degraded_mode_node,
)


# ── Routing functions (conditional edges) ──


def route_after_monitoring(state: SmartHomeState) -> str:
    """After reading sensors: critical bypass, evaluate, or loop."""
    if state.get("error_type") == "mcp_unreachable":
        return "error_handler"
    if state.get("gas_ppm", 0) > 1020 or state.get("temperature", 0) > 30.0:
        return "critical_handler"
    return "evaluating"


def route_after_evaluating(state: SmartHomeState) -> str:
    """After evaluation: decide if anomaly, normalize, or notify."""
    # Normalization: 3 consecutive normal readings after a critical event
    if state.get("normal_readings", 0) >= 3 and state.get("last_critical"):
        return "normalize"  # sentinel → go back to IDLE equivalent

    if state.get("anomaly_detected") or state.get("trend_rising"):
        return "deciding"

    # Normal readings — still consult LLM every 5th cycle for reasoned output,
    # otherwise notify directly (avoids burning tokens on redundant "all normal" reasoning)
    if state.get("cycle_count", 0) % 5 == 0:
        return "deciding"

    return "notifying"


def route_after_deciding(state: SmartHomeState) -> str:
    """After LLM decision: execute, confirm, idle, or error."""
    if state.get("error_type") in ("llm_timeout", "llm_error"):
        return "error_handler"

    decision = state.get("llm_decision", {})
    confidence = decision.get("confidence", 0)

    if state.get("needs_confirmation"):
        return "waiting_confirmation"

    if confidence >= 0.8 or state.get("critical_active"):
        return "executing"

    if decision.get("nivel") in ("normal", "info") or decision.get("accion") in ("no_action", "none"):
        return "notifying"  # publish "normal" decision, no actuators

    # Low confidence on a risky action
    return "executing"  # default: execute anyway (fallback already handled low confidence)


def route_after_executing(state: SmartHomeState) -> str:
    """After execution: notify success, or handle error."""
    if state.get("error_type") == "mcp_execution_fail":
        return "error_handler"
    return "notifying"


def route_after_receiving(state: SmartHomeState) -> str:
    """After intent classification: route based on classified_intent."""
    intent = state.get("classified_intent", "ambiguous")
    routing = {
        "command_silence": "command_router",
        "command_status": "command_router",
        "command_help": "command_router",
        "direct_action": "direct_exec",
        "query": "query_handler",
        "response_confirm": "executing",  # user confirmed → execute pending
        "response_reject": "notifying",    # user rejected → notify cancellation
        "contextual_action": "deciding",    # needs full evaluation
    }
    target = routing.get(intent, "waiting_clarification")
    return target


def route_after_confirm(state: SmartHomeState) -> str:
    """After user confirmation response."""
    response = state.get("user_response", "")
    if response == "approved":
        return "executing"
    return "notifying"  # rejected or timeout → notify cancellation


def route_after_error(state: SmartHomeState) -> str:
    """After error handling: recover or degrade."""
    if state.get("mode") == "degraded":
        return "degraded_mode"
    if state.get("retry_count", 0) <= state.get("max_retries", 3):
        return "monitoring"  # retry the cycle
    return "notifying"  # give up this cycle, notify and go back


def route_after_command_router(state: SmartHomeState) -> str:
    """After command router: route silence to silenced node, else notify."""
    intent = state.get("classified_intent")
    if intent == "command_silence":
        return "silenced"
    if state.get("critical_active"):
        return "critical_handler"
    return "notifying"


def route_after_silenced(state: SmartHomeState) -> str:
    """After silenced node: critical override or stay silenced."""
    if state.get("critical_active"):
        return "critical_handler"
    if state.get("normal_readings", 0) >= 3:
        return "notifying"  # exit silenced, notify normalization
    return "notifying"  # stay silenced, publish status


# ── Graph construction ──


def build_graph() -> StateGraph:
    """Build and compile the SmartHome agent StateGraph.

    Uses MemorySaver for in-memory checkpointing (state lost on restart).
    """
    builder = StateGraph(SmartHomeState)

    # Add all 15 nodes
    builder.add_node("monitoring", monitoring_node)
    builder.add_node("evaluating", evaluating_node)
    builder.add_node("critical_handler", critical_handler_node)
    builder.add_node("deciding", deciding_node)
    builder.add_node("executing", executing_node)
    builder.add_node("notifying", notifying_node)
    builder.add_node("receiving_input", receiving_input_node)
    builder.add_node("command_router", command_router_node)
    builder.add_node("query_handler", query_handler_node)
    builder.add_node("direct_exec", direct_exec_node)
    builder.add_node("waiting_confirmation", waiting_confirmation_node)
    builder.add_node("waiting_clarification", waiting_clarification_node)
    builder.add_node("silenced", silenced_node)
    builder.add_node("error_handler", error_handler_node)
    builder.add_node("degraded_mode", degraded_mode_node)

    # ── Entry points ──
    # Autonomous monitoring cycle
    builder.add_edge(START, "monitoring")

    # ── Monitoring flow ──
    builder.add_conditional_edges("monitoring", route_after_monitoring, {
        "critical_handler": "critical_handler",
        "evaluating": "evaluating",
        "error_handler": "error_handler",
    })

    # ── Evaluation flow ──
    builder.add_conditional_edges("evaluating", route_after_evaluating, {
        "deciding": "deciding",
        "notifying": "notifying",
        "normalize": "notifying",  # normalization → notify and go back
    })

    # ── Critical handler → execute immediately ──
    builder.add_edge("critical_handler", "executing")

    # ── Decision flow ──
    builder.add_conditional_edges("deciding", route_after_deciding, {
        "executing": "executing",
        "waiting_confirmation": "waiting_confirmation",
        "notifying": "notifying",
        "error_handler": "error_handler",
    })

    # ── Execution flow ──
    builder.add_conditional_edges("executing", route_after_executing, {
        "notifying": "notifying",
        "error_handler": "error_handler",
    })

    # ── User input flow ──
    # User input is triggered externally via graph.invoke with user_input_raw set
    # When user_input_raw is present, we route from START to receiving_input
    # For autonomous cycles, we always start at monitoring
    builder.add_conditional_edges("receiving_input", route_after_receiving, {
        "command_router": "command_router",
        "direct_exec": "direct_exec",
        "query_handler": "query_handler",
        "executing": "executing",
        "notifying": "notifying",
        "deciding": "deciding",
        "waiting_clarification": "waiting_clarification",
    })

    # ── Command routing ──
    builder.add_conditional_edges("command_router", route_after_command_router, {
        "silenced": "silenced",
        "critical_handler": "critical_handler",
        "notifying": "notifying",
    })

    # ── Direct exec → execute ──
    builder.add_edge("direct_exec", "executing")

    # ── Query → notify result ──
    builder.add_edge("query_handler", "notifying")

    # ── Waiting confirmation → user responds ──
    builder.add_conditional_edges("waiting_confirmation", route_after_confirm, {
        "executing": "executing",
        "notifying": "notifying",
    })

    # ── Waiting clarification → user re-input ──
    # Back to IDLE — user needs to send a new message
    builder.add_edge("waiting_clarification", "notifying")

    # ── Silenced → critical override or stay ──
    builder.add_conditional_edges("silenced", route_after_silenced, {
        "critical_handler": "critical_handler",
        "notifying": "notifying",
    })

    # ── Notifying → back to START (next cycle) ──
    builder.add_edge("notifying", END)

    # ── Error handling ──
    builder.add_conditional_edges("error_handler", route_after_error, {
        "degraded_mode": "degraded_mode",
        "monitoring": "monitoring",
        "notifying": "notifying",
    })

    # ── Degraded → notify and end ──
    builder.add_edge("degraded_mode", "notifying")

    # Compile with in-memory checkpointer
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


def build_graph_with_user_entry() -> StateGraph:
    """Build graph that also supports user input as entry point.

    This version adds a conditional edge from START that routes to
    either monitoring or receiving_input based on whether user_input_raw
    is present in the initial state.
    """
    builder = StateGraph(SmartHomeState)

    # Add all nodes (same as build_graph)
    builder.add_node("monitoring", monitoring_node)
    builder.add_node("evaluating", evaluating_node)
    builder.add_node("critical_handler", critical_handler_node)
    builder.add_node("deciding", deciding_node)
    builder.add_node("executing", executing_node)
    builder.add_node("notifying", notifying_node)
    builder.add_node("receiving_input", receiving_input_node)
    builder.add_node("command_router", command_router_node)
    builder.add_node("query_handler", query_handler_node)
    builder.add_node("direct_exec", direct_exec_node)
    builder.add_node("waiting_confirmation", waiting_confirmation_node)
    builder.add_node("waiting_clarification", waiting_clarification_node)
    builder.add_node("silenced", silenced_node)
    builder.add_node("error_handler", error_handler_node)
    builder.add_node("degraded_mode", degraded_mode_node)

    # Entry point: route based on whether there's user input
    def entry_router(state: SmartHomeState) -> str:
        if state.get("user_input_raw"):
            return "receiving_input"
        return "monitoring"

    builder.add_conditional_edges(START, entry_router, {
        "receiving_input": "receiving_input",
        "monitoring": "monitoring",
    })

    # ── All the same edges as build_graph ──
    builder.add_conditional_edges("monitoring", route_after_monitoring, {
        "critical_handler": "critical_handler",
        "evaluating": "evaluating",
        "error_handler": "error_handler",
    })
    builder.add_conditional_edges("evaluating", route_after_evaluating, {
        "deciding": "deciding",
        "notifying": "notifying",
        "normalize": "notifying",
    })
    builder.add_edge("critical_handler", "executing")
    builder.add_conditional_edges("deciding", route_after_deciding, {
        "executing": "executing",
        "waiting_confirmation": "waiting_confirmation",
        "notifying": "notifying",
        "error_handler": "error_handler",
    })
    builder.add_conditional_edges("executing", route_after_executing, {
        "notifying": "notifying",
        "error_handler": "error_handler",
    })
    builder.add_conditional_edges("receiving_input", route_after_receiving, {
        "command_router": "command_router",
        "direct_exec": "direct_exec",
        "query_handler": "query_handler",
        "executing": "executing",
        "notifying": "notifying",
        "deciding": "deciding",
        "waiting_clarification": "waiting_clarification",
    })
    builder.add_conditional_edges("command_router", route_after_command_router, {
        "silenced": "silenced",
        "critical_handler": "critical_handler",
        "notifying": "notifying",
    })
    builder.add_edge("direct_exec", "executing")
    builder.add_edge("query_handler", "notifying")
    builder.add_conditional_edges("waiting_confirmation", route_after_confirm, {
        "executing": "executing",
        "notifying": "notifying",
    })
    builder.add_edge("waiting_clarification", "notifying")
    builder.add_conditional_edges("silenced", route_after_silenced, {
        "critical_handler": "critical_handler",
        "notifying": "notifying",
    })
    builder.add_edge("notifying", END)
    builder.add_conditional_edges("error_handler", route_after_error, {
        "degraded_mode": "degraded_mode",
        "monitoring": "monitoring",
        "notifying": "notifying",
    })
    builder.add_edge("degraded_mode", "notifying")

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# ── Module-level agent instances ──
# Autonomous monitoring agent (timer-driven)
agent = build_graph()

# Dual-entry agent (supports both timer and user input)
agent_with_user = build_graph_with_user_entry()
