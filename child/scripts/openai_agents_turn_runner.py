"""OpenAI Agents SDK — Unified Turn Runner for qingxinyuma Electron IDE.

Integrates the full feature set of openai-agents SDK v0.14+:
- Agent lifecycle hooks (AgentHooks)
- Structured output types (output_type / Pydantic)
- ModelSettings per-agent and RunConfig global
- Dynamic instructions (function-based)
- tool_use_behavior (StopAtTools for specialists)
- Tool-level guardrails (ToolInputGuardrail)
- Hosted tools (WebSearchTool, FileSearchTool, CodeInterpreterTool, ImageGenerationTool)
- MultiProvider (per-agent model routing)
- Prompt API support
- nest_handoff_history + handoff_input_filter
- call_model_input_filter (context trimming)
- Simple-runner mode (merged from openai_agents_runner.py)
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
import uuid
from collections import defaultdict
from contextlib import AsyncExitStack
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from openai.types.responses import ResponseFunctionCallArgumentsDeltaEvent, ResponseTextDeltaEvent

from agents import (
    Agent,
    AgentHookContext,
    AgentHooks,
    FunctionTool,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    MaxTurnsExceeded,
    ModelSettings,
    MultiProvider,
    OpenAIChatCompletionsModel,
    OpenAIProvider,
    OpenAIResponsesModel,
    OutputGuardrailTripwireTriggered,
    Prompt,
    RunConfig,
    RunContextWrapper,
    RunState,
    Runner,
    SQLiteSession,
    StopAtTools,
    ToolInputGuardrail,
    ToolInputGuardrailData,
    ToolInputGuardrailTripwireTriggered,
    input_guardrail,
    output_guardrail,
    gen_trace_id,
    set_tracing_disabled,
    set_tracing_export_api_key,
    trace,
)
from agents.mcp import MCPServerStdio

# Conditional imports for hosted tools (OpenAI-only)
try:
    from agents import (
        WebSearchTool,
        FileSearchTool,
        CodeInterpreterTool,
        ImageGenerationTool,
        HostedMCPTool,
    )
    HOSTED_TOOLS_AVAILABLE = True
except ImportError:
    HOSTED_TOOLS_AVAILABLE = False

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


# ---------------------------------------------------------------------------
# Structured Output Types
# ---------------------------------------------------------------------------

if PYDANTIC_AVAILABLE:
    class SpecialistResult(BaseModel):
        """Structured output for specialist agent delegation."""
        summary: str = Field(description="Brief summary of what was accomplished or found")
        details: str = Field(description="Detailed findings, code, or instructions")
        status: str = Field(description="Status: success | partial | error")
        recommendations: list[str] = Field(default_factory=list, description="Follow-up recommendations")
        files_affected: list[str] = Field(default_factory=list, description="Files that were read, created, or modified")

    class DiagnosticReport(BaseModel):
        """Structured output for build/error diagnostics."""
        issues_found: int = Field(description="Number of issues found")
        critical: list[str] = Field(default_factory=list, description="Critical issues requiring immediate attention")
        warnings: list[str] = Field(default_factory=list, description="Warnings and non-critical issues")
        suggestions: list[str] = Field(default_factory=list, description="Improvement suggestions")
        build_status: str = Field(description="Build status: pass | fail | unknown")

    class FileOperationPlan(BaseModel):
        """Structured output for file operations."""
        operations: list[dict[str, Any]] = Field(description="List of file operations to perform")
        rationale: str = Field(description="Why these operations are needed")
        risk_level: str = Field(description="Risk level: low | medium | high")

    class SearchResults(BaseModel):
        """Structured output for research/search results."""
        query: str = Field(description="The original search query")
        results: list[dict[str, Any]] = Field(description="Search results with title, url, snippet")
        total_found: int = Field(description="Total results found")
        relevance_summary: str = Field(description="Summary of relevance to the task")

    SPECIALIST_RESULT_TYPE = SpecialistResult
    DIAGNOSTIC_REPORT_TYPE = DiagnosticReport
    FILE_OPERATION_TYPE = FileOperationPlan
    SEARCH_RESULTS_TYPE = SearchResults
else:
    SPECIALIST_RESULT_TYPE = None
    DIAGNOSTIC_REPORT_TYPE = None
    FILE_OPERATION_TYPE = None
    SEARCH_RESULTS_TYPE = None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAIN_AGENT_INSTRUCTIONS = (
    "You are the orchestration agent inside an Electron coding application. "
    "Prefer delegating work to the most appropriate specialist agent instead of doing all work yourself. "
    "Use direct tools only for lightweight coordination tasks like asking the user for clarification. "
    "Delegate only when it materially improves the answer, keep specialist usage focused, and stop exploring once you have enough evidence. "
    "Avoid repeated filesystem discovery or repeated diagnostics unless the user explicitly asks for deeper investigation. "
    "If you create a todo list or test plan, continue executing it in the same run instead of stopping after planning, unless the user explicitly asks for plan-only output. "
    "Keep answers concise and combine specialist outputs into one coherent response."
)

SCHEMATIC_AGENT_INSTRUCTIONS = (
    "You specialize in schematic, pin mapping, board wiring, and hardware integration tasks. "
    "Use the provided tools to inspect the project and return concrete wiring or schematic guidance."
)

SPECIALIST_AGENT_DEFS = [
    {
        "key": "project",
        "name": "ProjectSpecialist",
        "instructions": (
            "You specialize in project creation, board switching, project configuration, build execution, "
            "repository cloning, architecture notes, and project-level diagnostics. "
            "Do not call get_errors unless the user explicitly asks for build or lint diagnostics. "
            "Avoid repeated diagnostics after one result is available. "
            "Prefer finishing concrete project actions such as create_project, switch_board, and set_board_config before stopping. "
            "Only stop early after 1-2 key findings when the task is analysis-only."
        ),
        "output_type": DIAGNOSTIC_REPORT_TYPE,
        "matcher": lambda name: name in {
            "create_project", "build_project", "reload_project", "switch_board",
            "get_board_config", "set_board_config", "get_context", "get_project_context",
            "get_project_info", "save_arch", "clone_repository", "get_errors", "memory",
        },
    },
    {
        "key": "file",
        "name": "FileSpecialist",
        "instructions": (
            "You specialize in reading, creating, editing, replacing, and organizing files and folders. "
            "Use file and search tools to inspect and modify project content precisely. "
            "Prefer one broad directory read before narrower file reads, and avoid repeating the same discovery tool. "
            "You must stop after collecting 1-2 key structural findings, and you have a hard cap of 2 tool calls in a handoff."
        ),
        "output_type": FILE_OPERATION_TYPE,
        "matcher": lambda name: name in {
            "read_file", "create_file", "edit_file", "replace_string_in_file",
            "multi_replace_string_in_file", "delete_file", "delete_folder", "create_folder",
            "list_directory", "get_directory_tree", "grep_tool", "glob_tool",
            "get_context", "get_project_info", "get_project_context",
        },
    },
    {
        "key": "terminal",
        "name": "TerminalSpecialist",
        "instructions": (
            "You specialize in shell commands, background processes, terminal output, and environment inspection. "
            "Use terminal tools carefully and summarize command results clearly. "
            "Avoid loops of repeated command execution. "
            "You must stop after collecting 1-2 key environment findings, and you have a hard cap of 2 tool calls in a handoff."
        ),
        "output_type": DIAGNOSTIC_REPORT_TYPE,
        "matcher": lambda name: name in {
            "execute_command", "start_background_command", "get_terminal_output",
        },
    },
    {
        "key": "blockly",
        "name": "BlocklySpecialist",
        "instructions": (
            "You specialize in Blockly, block search, ABS syntax, library block analysis, "
            "block creation, structure generation, and code generation diagnostics. "
            "When the user asks to build or edit blocks, prefer using Blockly tools directly "
            "instead of stopping at analysis."
        ),
        "output_type": SPECIALIST_RESULT_TYPE,
        "matcher": lambda name: name in {
            "search_blocks_by_keyword", "smart_block_tool", "connect_blocks_tool",
            "create_code_structure_tool", "configure_block_tool", "delete_block_tool",
            "get_workspace_overview_tool", "queryBlockDefinitionTool", "analyze_library_blocks",
            "get_abs_syntax", "verify_block_existence", "dsl_create_blocks", "arduino_syntax_check",
        },
    },
    {
        "key": "research",
        "name": "ResearchSpecialist",
        "instructions": (
            "You specialize in searching available tools, loading skills, fetching remote content, "
            "and hardware or library discovery. Prefer research-oriented tools first and avoid using "
            "file-editing tools unless the user explicitly asks for file changes."
        ),
        "output_type": SEARCH_RESULTS_TYPE,
        "matcher": lambda name: name in {
            "search_available_tools", "load_skill", "fetch",
            "search_boards_libraries", "get_component_catalog", "get_pinmap_summary",
        },
    },
]

SECRET_REQUEST_PATTERNS = [
    re.compile(r"\b(api[_ -]?key|access[_ -]?token|secret|password|private[_ -]?key)\b", re.I),
    re.compile(r"\b(show|reveal|print|dump|导出|显示|泄露).{0,20}\b(api[_ -]?key|token|secret|密码|私钥)\b", re.I),
]
SECRET_OUTPUT_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
]

# Tools that require extra caution — tool-level guardrails
DESTRUCTIVE_TOOLS = {"delete_file", "delete_folder", "execute_command", "start_background_command"}

MAX_TOTAL_TOOL_CALLS = 18
DEFAULT_TOOL_CALL_LIMIT = 4
SPECIALIST_FIRST_ROUND_MAX_TOOL_CALLS = 2
TOOL_CALL_LIMITS = {
    "get_errors": 1,
    "build_project": 1,
    "execute_command": 2,
    "start_background_command": 1,
    "get_directory_tree": 1,
    "list_directory": 2,
    "glob_tool": 2,
    "grep_tool": 2,
    "get_project_context": 1,
    "get_project_info": 1,
    "get_context": 1,
    "search_available_tools": 1,
    "load_skill": 1,
    "search_blocks_by_keyword": 8,
    "smart_block_tool": 6,
    "create_code_structure_tool": 4,
    "configure_block_tool": 6,
    "connect_blocks_tool": 6,
}
GET_ERRORS_FAST_DEGRADE_MESSAGE = (
    "get_errors failed or diagnostics are currently unavailable. "
    "Do not retry get_errors in this run. "
    "Return a concise risk summary based on the project structure, board config, and any evidence already collected."
)

# Per-specialist ModelSettings profiles
SPECIALIST_MODEL_PROFILES: dict[str, dict[str, Any]] = {
    "ProjectSpecialist": {"temperature": 0.2, "max_tokens": 4096},
    "FileSpecialist": {"temperature": 0.0, "max_tokens": 2048},
    "TerminalSpecialist": {"temperature": 0.1, "max_tokens": 2048},
    "BlocklySpecialist": {"temperature": 0.3, "max_tokens": 4096},
    "ResearchSpecialist": {"temperature": 0.5, "max_tokens": 4096},
    "schematicAgent": {"temperature": 0.2, "max_tokens": 4096},
}


# ---------------------------------------------------------------------------
# Hook Metrics Dataclass
# ---------------------------------------------------------------------------

@dataclass
class HookMetrics:
    """Tracks timing and counts for agent lifecycle events."""
    agent_name: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    llm_calls: int = 0
    llm_total_ms: float = 0.0
    tool_calls: int = 0
    tool_total_ms: float = 0.0
    handoffs: int = 0
    tool_names: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["total_ms"] = round((self.end_time - self.start_time) * 1000, 1) if self.end_time else 0
        d["llm_avg_ms"] = round(self.llm_total_ms / self.llm_calls, 1) if self.llm_calls else 0
        d["tool_avg_ms"] = round(self.tool_total_ms / self.tool_calls, 1) if self.tool_calls else 0
        return d


# ---------------------------------------------------------------------------
# Agent Lifecycle Hooks
# ---------------------------------------------------------------------------

class LoggingAgentHooks(AgentHooks[Any]):
    """Lifecycle hooks that emit timing/metrics events to Angular."""

    def __init__(self) -> None:
        self._active_metrics: dict[str, HookMetrics] = {}
        self._tool_start_times: dict[str, float] = {}

    def _get_or_create(self, agent_name: str) -> HookMetrics:
        if agent_name not in self._active_metrics:
            self._active_metrics[agent_name] = HookMetrics(agent_name=agent_name)
        return self._active_metrics[agent_name]

    async def on_start(self, context: RunContextWrapper[Any], agent: Agent[Any]) -> None:
        m = self._get_or_create(agent.name)
        m.start_time = time.monotonic()
        emit({
            "type": "hook_event",
            "hook": "on_start",
            "agent_name": agent.name,
            "timestamp": m.start_time,
        })

    async def on_llm_start(self, context: RunContextWrapper[Any], agent: Agent[Any], messages: Any) -> None:
        m = self._get_or_create(agent.name)
        m.llm_calls += 1
        self._tool_start_times[f"llm_{agent.name}_{m.llm_calls}"] = time.monotonic()
        emit({
            "type": "hook_event",
            "hook": "on_llm_start",
            "agent_name": agent.name,
            "llm_call_number": m.llm_calls,
        })

    async def on_llm_end(self, context: RunContextWrapper[Any], agent: Agent[Any], response: Any) -> None:
        m = self._get_or_create(agent.name)
        key = f"llm_{agent.name}_{m.llm_calls}"
        if key in self._tool_start_times:
            elapsed = time.monotonic() - self._tool_start_times.pop(key)
            m.llm_total_ms += elapsed * 1000
        emit({
            "type": "hook_event",
            "hook": "on_llm_end",
            "agent_name": agent.name,
            "llm_call_number": m.llm_calls,
            "elapsed_ms": round(elapsed * 1000, 1) if 'elapsed' in dir() else 0,
        })

    async def on_tool_start(self, context: RunContextWrapper[Any], agent: Agent[Any], tool: Any) -> None:
        m = self._get_or_create(agent.name)
        m.tool_calls += 1
        tool_name = getattr(tool, "name", str(tool))
        m.tool_names.append(tool_name)
        tool_key = f"tool_{agent.name}_{m.tool_calls}"
        self._tool_start_times[tool_key] = time.monotonic()
        emit({
            "type": "hook_event",
            "hook": "on_tool_start",
            "agent_name": agent.name,
            "tool_name": tool_name,
            "tool_call_number": m.tool_calls,
        })

    async def on_tool_end(self, context: RunContextWrapper[Any], agent: Agent[Any], tool: Any, result: str) -> None:
        m = self._get_or_create(agent.name)
        tool_key = f"tool_{agent.name}_{m.tool_calls}"
        elapsed = 0.0
        if tool_key in self._tool_start_times:
            elapsed = time.monotonic() - self._tool_start_times.pop(tool_key)
            m.tool_total_ms += elapsed * 1000
        tool_name = getattr(tool, "name", str(tool))
        emit({
            "type": "hook_event",
            "hook": "on_tool_end",
            "agent_name": agent.name,
            "tool_name": tool_name,
            "elapsed_ms": round(elapsed * 1000, 1),
            "result_length": len(result) if isinstance(result, str) else 0,
        })

    async def on_handoff(self, context: RunContextWrapper[Any], agent: Agent[Any], source: Agent[Any]) -> None:
        m = self._get_or_create(agent.name)
        m.handoffs += 1
        emit({
            "type": "hook_event",
            "hook": "on_handoff",
            "agent_name": agent.name,
            "source_agent": source.name,
            "handoff_number": m.handoffs,
        })

    async def on_end(self, context: RunContextWrapper[Any], agent: Agent[Any], output: Any) -> None:
        m = self._get_or_create(agent.name)
        m.end_time = time.monotonic()
        emit({
            "type": "hook_event",
            "hook": "on_end",
            "agent_name": agent.name,
            "metrics": m.to_dict(),
        })

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        return {name: m.to_dict() for name, m in self._active_metrics.items()}


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def normalize_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        normalized = normalized[: -len("/chat/completions")]
    return normalized


def emit(event: dict) -> None:
    print(json.dumps(event, ensure_ascii=False), flush=True)


def read_stdin_event(expected_type: str | None = None, expected_id: str | None = None) -> dict:
    while True:
        line = sys.stdin.readline()
        if not line:
            raise RuntimeError("stdin closed while waiting for runner event")
        payload = line.strip()
        if not payload:
            continue
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if expected_type and data.get("type") != expected_type:
            continue
        if expected_id and data.get("tool_id") != expected_id and data.get("call_id") != expected_id:
            continue
        return data


# ---------------------------------------------------------------------------
# Tool Budget Tracker
# ---------------------------------------------------------------------------

class ToolBudgetTracker:
    def __init__(
        self,
        name: str,
        max_total_calls: int,
        default_tool_limit: int = DEFAULT_TOOL_CALL_LIMIT,
        per_tool_limits: dict[str, int] | None = None,
    ) -> None:
        self.name = name
        self.max_total_calls = max_total_calls
        self.default_tool_limit = default_tool_limit
        self.per_tool_limits = per_tool_limits or {}
        self.total_calls = 0
        self.per_tool_calls: dict[str, int] = defaultdict(int)
        self.blocked_tools: set[str] = set()

    def increment(self, tool_name: str) -> dict[str, Any]:
        if tool_name in self.blocked_tools:
            return {"blocked": True, "reason": "blocked_after_failure", "tracker": self.name}
        tool_limit = self.per_tool_limits.get(tool_name, self.default_tool_limit)
        if self.total_calls >= self.max_total_calls:
            return {"blocked": True, "reason": "total_budget", "tracker": self.name}
        if self.per_tool_calls[tool_name] >= tool_limit:
            return {"blocked": True, "reason": "tool_budget", "tracker": self.name}
        self.total_calls += 1
        self.per_tool_calls[tool_name] += 1
        return {"blocked": False, "reason": "", "tracker": self.name}

    def block_tool(self, tool_name: str) -> None:
        self.blocked_tools.add(tool_name)


GLOBAL_TOOL_BUDGETS = ToolBudgetTracker(
    name="global",
    max_total_calls=MAX_TOTAL_TOOL_CALLS,
    default_tool_limit=DEFAULT_TOOL_CALL_LIMIT,
    per_tool_limits=TOOL_CALL_LIMITS,
)


def build_budget_stop_message(tool_name: str, reason: str, agent_name: str | None = None) -> str:
    subject = agent_name or "Current specialist"
    if tool_name == "get_errors" and reason == "blocked_after_failure":
        return GET_ERRORS_FAST_DEGRADE_MESSAGE
    if reason == "total_budget":
        return (
            f"{subject} has reached its tool budget. "
            "Stop now and return the 1-2 most important findings already collected."
        )
    if reason == "tool_budget":
        return (
            f"{tool_name} has already been used enough in this handoff. "
            "Do not repeat it. Summarize the current evidence and stop."
        )
    if reason == "blocked_after_failure":
        return (
            f"{tool_name} previously failed in this handoff. "
            "Do not retry it. Report the limitation briefly and return with the evidence already available."
        )
    return (
        f"Stop using {tool_name}. "
        "Return the key findings collected so far instead of continuing tool exploration."
    )


# ---------------------------------------------------------------------------
# Model Config Resolution
# ---------------------------------------------------------------------------

def resolve_model_config(config: dict) -> tuple[str, str | None, str]:
    api_key = (config.get("apiKey") or "").strip() or os.environ.get("OPENAI_API_KEY", "").strip()
    base_url = (config.get("baseUrl") or "").strip() or os.environ.get("OPENAI_BASE_URL", "").strip()
    model = (config.get("model") or "").strip() or os.environ.get("OPENAI_MODEL", "").strip()
    if not api_key:
        raise RuntimeError("Missing API key. Configure a custom model or set OPENAI_API_KEY.")
    if not model:
        raise RuntimeError("Missing model name. Select a custom model or set OPENAI_MODEL.")
    return api_key, normalize_base_url(base_url), model


def should_enable_tracing(base_url: str | None) -> bool:
    if not base_url:
        return True
    return "api.openai.com" in base_url.lower()


def should_use_responses_api(base_url: str | None) -> bool:
    if not base_url:
        return True
    normalized = base_url.lower()
    return "api.openai.com" in normalized


def build_trace_url(trace_id: str) -> str:
    return f"https://platform.openai.com/traces/trace?trace_id={trace_id}"


def ensure_parent_dir(file_path: str) -> None:
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# MCP Server Builder
# ---------------------------------------------------------------------------

def load_mcp_server_configs(config_path: str | None) -> list[dict[str, Any]]:
    if not config_path:
        return []
    file_path = Path(config_path)
    if not file_path.exists():
        return []
    data = json.loads(file_path.read_text(encoding="utf-8"))
    servers = data.get("mcpServers") or {}
    out: list[dict[str, Any]] = []
    for name, conf in servers.items():
        if not conf or conf.get("enabled") is False:
            continue
        out.append({"name": name, "command": conf.get("command"), "args": conf.get("args") or []})
    return [item for item in out if item["command"]]


async def build_mcp_servers(stack: AsyncExitStack, config_path: str | None) -> list[Any]:
    servers: list[Any] = []
    for conf in load_mcp_server_configs(config_path):
        server = await stack.enter_async_context(
            MCPServerStdio(
                name=conf["name"],
                params={"command": conf["command"], "args": conf["args"]},
            )
        )
        servers.append(server)
    return servers


# ---------------------------------------------------------------------------
# Hosted Tool Builder (OpenAI Responses API only)
# ---------------------------------------------------------------------------

def build_hosted_tools(request: dict, use_responses_api: bool) -> list[Any]:
    """Build OpenAI-hosted tools from request config. Only available on Responses API."""
    if not use_responses_api or not HOSTED_TOOLS_AVAILABLE:
        return []

    hosted_config = request.get("hostedTools") or {}
    tools: list[Any] = []

    if hosted_config.get("webSearch"):
        search_cfg = hosted_config["webSearch"]
        try:
            tools.append(WebSearchTool(
                search_context_size=search_cfg.get("contextSize", "medium"),
                user_location=search_cfg.get("userLocation"),
            ))
        except Exception:
            tools.append(WebSearchTool())

    if hosted_config.get("fileSearch"):
        fs_cfg = hosted_config["fileSearch"]
        vector_store_ids = fs_cfg.get("vectorStoreIds") or []
        if vector_store_ids:
            try:
                tools.append(FileSearchTool(
                    vector_store_ids=vector_store_ids,
                    max_num_results=fs_cfg.get("maxResults", 5),
                ))
            except Exception:
                pass

    if hosted_config.get("codeInterpreter"):
        ci_cfg = hosted_config["codeInterpreter"]
        try:
            tools.append(CodeInterpreterTool(
                container=ci_cfg.get("container", {"type": "auto"}),
            ))
        except Exception:
            pass

    if hosted_config.get("imageGeneration"):
        ig_cfg = hosted_config["imageGeneration"]
        try:
            tools.append(ImageGenerationTool(
                quality=ig_cfg.get("quality", "auto"),
                size=ig_cfg.get("size", "auto"),
            ))
        except Exception:
            pass

    if hosted_config.get("hostedMCP"):
        for mcp_def in hosted_config["hostedMCP"]:
            try:
                tools.append(HostedMCPTool(
                    tool_config=mcp_def.get("toolConfig", {}),
                    approval=mcp_def.get("approval", "never"),
                ))
            except Exception:
                pass

    return tools


# ---------------------------------------------------------------------------
# Dynamic Instructions
# ---------------------------------------------------------------------------

async def make_dynamic_instructions(
    base_instructions: str,
    project_context: dict[str, Any] | None = None,
) -> Any:
    """Create a function-based dynamic instructions provider.

    When project_context is provided, appends project-aware guidance to the base
    instructions so the agent adapts to the current project state.
    """
    if not project_context:
        return base_instructions

    project_name = project_context.get("projectName", "unknown")
    board_type = project_context.get("boardType", "unknown")
    recent_files = project_context.get("recentFiles", [])[:5]

    async def _dynamic(ctx: RunContextWrapper[Any], agent: Agent[Any]) -> str:
        parts = [base_instructions]
        parts.append(f"\n\n## Current Project Context")
        parts.append(f"- Project: {project_name}")
        parts.append(f"- Board: {board_type}")
        if recent_files:
            parts.append(f"- Recently accessed files: {', '.join(recent_files)}")
        return "\n".join(parts)

    return _dynamic


# ---------------------------------------------------------------------------
# Call Model Input Filter (Context Trimming)
# ---------------------------------------------------------------------------

async def context_trimming_filter(
    agent: Any,
    context: RunContextWrapper[Any],
    input_data: Any,
) -> Any:
    """Trim model input to stay within a reasonable context window.

    When conversation history grows too long, this collapses older messages
    to prevent token overflow while preserving the most recent context.
    """
    max_input_items = 80
    if not isinstance(input_data, dict):
        return input_data

    items = input_data.get("input") or input_data.get("messages") or []
    if not isinstance(items, list) or len(items) <= max_input_items:
        return input_data

    # Keep system messages + first 2 items + last (max_input_items - 4) items
    system_items = [item for item in items[:3] if isinstance(item, dict) and item.get("role") == "system"]
    non_system = [item for item in items if not (isinstance(item, dict) and item.get("role") == "system")]
    if len(non_system) > max_input_items - len(system_items):
        kept = non_system[-(max_input_items - len(system_items)):]
        # Add a summarization marker
        collapsed_count = len(non_system) - len(kept)
        collapsed_marker = {
            "role": "assistant",
            "content": f"[{collapsed_count} earlier messages collapsed to save context space]",
        }
        items = [*system_items, collapsed_marker, *kept]
    else:
        items = [*system_items, *non_system]

    result = dict(input_data)
    if "input" in result:
        result["input"] = items
    elif "messages" in result:
        result["messages"] = items
    return result


# ---------------------------------------------------------------------------
# Tool-Level Guardrails
# ---------------------------------------------------------------------------

def create_destructive_tool_guardrail() -> Any:
    """ToolInputGuardrail that flags destructive tool calls for extra scrutiny."""

    async def _check_destructive(
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        tool: Any,
        tool_input: str,
    ) -> GuardrailFunctionOutput:
        tool_name = getattr(tool, "name", "")
        if tool_name not in DESTRUCTIVE_TOOLS:
            return GuardrailFunctionOutput(
                output_info={"tool": tool_name, "flagged": False},
                tripwire_triggered=False,
            )

        # Parse tool input for dangerous patterns
        try:
            args = json.loads(tool_input) if tool_input else {}
        except (json.JSONDecodeError, TypeError):
            args = {}

        # Check for system-wide deletions or dangerous commands
        path = str(args.get("path") or args.get("file_path") or args.get("command") or "")
        danger_patterns = [
            r"rm\s+-rf\s+/", r"format\s+[a-zA-Z]:", r"del\s+/[sfq]",
            r"\bsystem32\b", r"\bWindows\\", r"sudo\s+rm",
        ]
        is_dangerous = any(re.search(p, path, re.I) for p in danger_patterns)

        if is_dangerous:
            emit({
                "type": "tool_guardrail_warning",
                "tool_name": tool_name,
                "reason": "Potentially destructive operation detected",
                "input_preview": path[:200],
            })

        return GuardrailFunctionOutput(
            output_info={"tool": tool_name, "flagged": is_dangerous, "path": path[:200]},
            tripwire_triggered=False,  # Warn but don't block
        )

    return ToolInputGuardrail(
        name="destructive_tool_check",
        guardrail_function=_check_destructive,
    )


# ---------------------------------------------------------------------------
# Bridge Tool Factory
# ---------------------------------------------------------------------------

def create_bridge_tool(
    schema: dict,
    *,
    budget_trackers: list[ToolBudgetTracker] | None = None,
    agent_name: str | None = None,
) -> FunctionTool:
    name = schema["name"]
    description = schema.get("description") or ""
    params_json_schema = schema.get("input_schema") or {"type": "object", "properties": {}}
    requires_approval = bool(schema.get("requires_approval"))
    trackers = budget_trackers or [GLOBAL_TOOL_BUDGETS]

    async def on_invoke_tool(_ctx, args_json: str, *, tool_name: str = name):
        for tracker in trackers:
            budget_state = tracker.increment(tool_name)
            if budget_state["blocked"]:
                emit({
                    "type": "tool_budget_skip",
                    "tool_name": tool_name,
                    "reason": budget_state["reason"],
                    "tracker": budget_state.get("tracker") or tracker.name,
                    "agent_name": agent_name or "",
                })
                return build_budget_stop_message(tool_name, budget_state["reason"], agent_name)
        tool_id = f"oa_tool_{uuid.uuid4().hex}"
        emit({"type": "tool_call_request", "tool_id": tool_id, "tool_name": tool_name, "tool_args": args_json or "{}"})
        result = await asyncio.to_thread(read_stdin_event, "tool_result", tool_id)
        is_error = bool(result.get("is_error"))
        if tool_name == "get_errors" and is_error:
            for tracker in trackers:
                tracker.block_tool("get_errors")
            emit({
                "type": "tool_fast_degrade",
                "tool_name": "get_errors",
                "agent_name": agent_name or "",
                "reason": "tool_error",
            })
            return GET_ERRORS_FAST_DEGRADE_MESSAGE
        return result.get("content", "")

    return FunctionTool(
        name=name,
        description=description,
        params_json_schema=params_json_schema,
        on_invoke_tool=on_invoke_tool,
        needs_approval=requires_approval,
    )


def sanitize_tool_suffix(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_") or "agent"


def create_builtin_subagent_tool(agent_def: dict) -> FunctionTool:
    agent_name = agent_def["name"]
    display_name = agent_def.get("displayName") or agent_name
    description = agent_def.get("description") or f"Delegate work to builtin agent {display_name}"

    async def on_invoke_tool(_ctx, args_json: str):
        tool_id = f"oa_builtin_agent_{uuid.uuid4().hex}"
        emit({
            "type": "tool_call_request",
            "tool_id": tool_id,
            "tool_name": "run_subagent",
            "tool_args": json.dumps(
                {"agent": agent_name, **(json.loads(args_json or "{}"))},
                ensure_ascii=False,
            ),
        })
        result = await asyncio.to_thread(read_stdin_event, "tool_result", tool_id)
        return result.get("content", "")

    return FunctionTool(
        name=f"invoke_builtin_{sanitize_tool_suffix(agent_name)}",
        description=description,
        params_json_schema={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": f"Task to delegate to builtin agent {display_name}",
                },
                "context": {
                    "type": "string",
                    "description": "Optional extra context passed to the builtin agent",
                },
            },
            "required": ["task"],
        },
        on_invoke_tool=on_invoke_tool,
        needs_approval=True,
    )


# ---------------------------------------------------------------------------
# Specialist Tool Classification
# ---------------------------------------------------------------------------

def classify_specialist_tools(main_tools: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    coordinator_tools: list[dict[str, Any]] = []
    specialist_tools: dict[str, list[dict[str, Any]]] = {item["key"]: [] for item in SPECIALIST_AGENT_DEFS}
    shared_specialist_tools: list[dict[str, Any]] = []

    for tool in main_tools:
        name = tool["name"]
        if name == "ask_user":
            coordinator_tools.append(tool)
            shared_specialist_tools.append(tool)
            continue
        if name in {"load_skill", "search_available_tools"}:
            coordinator_tools.append(tool)
            specialist_tools["research"].append(tool)
            continue
        matched = False
        for specialist in SPECIALIST_AGENT_DEFS:
            if specialist["matcher"](name):
                specialist_tools[specialist["key"]].append(tool)
                matched = True
                break
        if not matched:
            coordinator_tools.append(tool)

    agents = []
    for specialist in SPECIALIST_AGENT_DEFS:
        tools = [*shared_specialist_tools, *specialist_tools[specialist["key"]]]
        if not tools:
            continue
        max_tc = 4 if specialist["name"] == "ProjectSpecialist" else SPECIALIST_FIRST_ROUND_MAX_TOOL_CALLS if specialist["name"] in {
            "ProjectSpecialist", "FileSpecialist", "TerminalSpecialist",
        } else 3
        agents.append({
            "name": specialist["name"],
            "instructions": specialist["instructions"],
            "output_type": specialist.get("output_type"),
            "tools": tools,
            "description": specialist["instructions"],
            "max_tool_calls": max_tc,
        })

    return coordinator_tools, agents


# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------

@input_guardrail
async def secret_request_guardrail(_context: RunContextWrapper[Any], _agent: Agent, input: str | list[Any]) -> GuardrailFunctionOutput:
    if isinstance(input, str):
        text = input
    else:
        text = json.dumps(input, ensure_ascii=False)
    triggered = any(pattern.search(text) for pattern in SECRET_REQUEST_PATTERNS)
    return GuardrailFunctionOutput(
        output_info={"reason": "secret_request", "matched": triggered},
        tripwire_triggered=triggered,
    )


@output_guardrail
async def secret_output_guardrail(_context: RunContextWrapper[Any], _agent: Agent, output: Any) -> GuardrailFunctionOutput:
    text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
    triggered = any(pattern.search(text) for pattern in SECRET_OUTPUT_PATTERNS)
    return GuardrailFunctionOutput(
        output_info={"reason": "secret_output", "matched": triggered},
        tripwire_triggered=triggered,
    )


# ---------------------------------------------------------------------------
# RunState Management
# ---------------------------------------------------------------------------

def save_run_state(run_state_path: str, state: RunState[Any]) -> None:
    if not run_state_path:
        return
    ensure_parent_dir(run_state_path)
    Path(run_state_path).write_text(json.dumps(state.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")


async def load_run_state(run_state_path: str, main_agent: Agent[Any]) -> RunState[Any] | None:
    if not run_state_path:
        return None
    file_path = Path(run_state_path)
    if not file_path.exists():
        return None
    payload = json.loads(file_path.read_text(encoding="utf-8-sig"))
    return await RunState.from_json(main_agent, payload)


def clear_run_state(run_state_path: str) -> None:
    if not run_state_path:
        return
    file_path = Path(run_state_path)
    if file_path.exists():
        file_path.unlink()


# ---------------------------------------------------------------------------
# Streaming Helper
# ---------------------------------------------------------------------------

async def stream_single_run(
    main_agent: Agent[Any],
    input_data: Any,
    session: SQLiteSession | None,
    max_turns: int,
    run_config: RunConfig | None = None,
):
    if not isinstance(input_data, RunState):
        result = Runner.run_streamed(main_agent, input_data, session=session, max_turns=max_turns, run_config=run_config)
    else:
        result = Runner.run_streamed(main_agent, input_data, max_turns=max_turns, run_config=run_config)
    async for event in result.stream_events():
        if event.type == "raw_response_event":
            raw = event.data
            emit({"type": "raw_response_event", "event_type": getattr(raw, "type", "unknown")})
            if isinstance(raw, ResponseTextDeltaEvent):
                emit({"type": "ModelClientStreamingChunkEvent", "content": raw.delta})
            elif isinstance(raw, ResponseFunctionCallArgumentsDeltaEvent):
                emit({
                    "type": "function_call_arguments_delta",
                    "call_id": getattr(raw, "item_id", None) or getattr(raw, "output_index", None),
                    "delta": raw.delta,
                })
        elif event.type == "run_item_stream_event":
            emit({"type": "run_item_stream_event", "name": event.name, "item_type": getattr(event.item, "type", "unknown")})
        elif event.type == "agent_updated_stream_event":
            emit({"type": "agent_updated_stream_event", "agent_name": event.new_agent.name})
    return result


# ---------------------------------------------------------------------------
# Main Turn Runner
# ---------------------------------------------------------------------------

async def run_turn(request: dict) -> str:
    model_config = request.get("modelConfig") or {}
    user_input = request.get("userInput") or request.get("transcript") or ""
    main_tools = request.get("mainTools") or request.get("tools") or []
    schematic_tools = request.get("schematicTools") or []
    built_in_agents = request.get("builtInAgents") or []
    session_id = request.get("sessionId") or f"local_{uuid.uuid4().hex}"
    session_db_path = request.get("sessionDbPath") or ":memory:"
    run_state_path = request.get("runStatePath") or ""
    mcp_config_path = request.get("mcpConfigPath")
    max_turns = max(20, int(request.get("maxTurns") or 40))
    project_context = request.get("projectContext")
    # New: global model settings override
    global_model_settings_cfg = request.get("modelSettings") or {}
    # New: whether to use hosted tools
    hosted_tools_cfg = request.get("hostedTools") or {}
    # New: prompt API config
    prompt_cfg = request.get("prompt")

    if not user_input.strip() and not run_state_path:
        raise RuntimeError("Missing user input content.")

    api_key, base_url, model_name = resolve_model_config(model_config)

    tracing_enabled = should_enable_tracing(base_url)
    set_tracing_disabled(not tracing_enabled)
    if tracing_enabled:
        set_tracing_export_api_key(api_key)

    client = AsyncOpenAI(api_key=api_key, base_url=base_url or None)
    use_responses_api = should_use_responses_api(base_url)
    emit({
        "type": "runner_info",
        "model_backend": "responses" if use_responses_api else "chat_completions",
        "model": model_name,
        "base_url": base_url or "",
        "features": {
            "structured_output": PYDANTIC_AVAILABLE,
            "hosted_tools": HOSTED_TOOLS_AVAILABLE and use_responses_api,
            "hooks": True,
            "dynamic_instructions": bool(project_context),
            "nest_handoff_history": True,
            "context_trimming": True,
            "tool_guardrails": True,
            "multi_provider": True,
            "prompt_api": bool(prompt_cfg),
        },
    })

    if use_responses_api:
        model = OpenAIResponsesModel(model=model_name, openai_client=client)
    else:
        model = OpenAIChatCompletionsModel(model=model_name, openai_client=client)

    # Build MultiProvider for potential per-agent model routing
    multi_provider = MultiProvider(
        default_factory=lambda _name: OpenAIProvider(
            api_key=api_key,
            base_url=base_url or None,
            use_responses=use_responses_api,
        )
    )

    if session_db_path != ":memory:":
        ensure_parent_dir(session_db_path)
    session = SQLiteSession(session_id, db_path=session_db_path)

    # Build global ModelSettings
    global_ms = ModelSettings()
    if global_model_settings_cfg:
        ms_kwargs: dict[str, Any] = {}
        if "temperature" in global_model_settings_cfg:
            ms_kwargs["temperature"] = float(global_model_settings_cfg["temperature"])
        if "maxTokens" in global_model_settings_cfg:
            ms_kwargs["max_tokens"] = int(global_model_settings_cfg["maxTokens"])
        if "topP" in global_model_settings_cfg:
            ms_kwargs["top_p"] = float(global_model_settings_cfg["topP"])
        if "frequencyPenalty" in global_model_settings_cfg:
            ms_kwargs["frequency_penalty"] = float(global_model_settings_cfg["frequency_penalty"])
        if "presencePenalty" in global_model_settings_cfg:
            ms_kwargs["presence_penalty"] = float(global_model_settings_cfg["presencePenalty"])
        if "toolChoice" in global_model_settings_cfg:
            ms_kwargs["tool_choice"] = global_model_settings_cfg["toolChoice"]
        if "parallelToolCalls" in global_model_settings_cfg:
            ms_kwargs["parallel_tool_calls"] = bool(global_model_settings_cfg["parallelToolCalls"])
        if "reasoning" in global_model_settings_cfg:
            ms_kwargs["reasoning"] = global_model_settings_cfg["reasoning"]
        if ms_kwargs:
            global_ms = ModelSettings(**ms_kwargs)

    # Build Prompt API reference if configured
    prompt_ref = None
    if prompt_cfg and isinstance(prompt_cfg, dict) and prompt_cfg.get("id"):
        prompt_ref = Prompt(
            id=prompt_cfg["id"],
            version=prompt_cfg.get("version"),
            variables=prompt_cfg.get("variables") or {},
        )

    # Build hosted tools
    hosted_tools = build_hosted_tools(request, use_responses_api)
    if hosted_tools:
        emit({"type": "hosted_tools_info", "tools": [type(t).__name__ for t in hosted_tools]})

    # Build tool-level guardrails (ready for future SDK wiring when Agent/RunConfig
    # expose tool_input_guardrails; currently unused — the function is kept for reference).
    # tool_guardrails = [create_destructive_tool_guardrail()]

    # Determine if web search is available for research specialist
    web_search_tool = None
    if hosted_tools:
        for t in hosted_tools:
            if type(t).__name__ == "WebSearchTool":
                web_search_tool = t
                break

    # Instantiate lifecycle hooks
    hooks = LoggingAgentHooks()

    # Build dynamic instructions
    dynamic_instructions = await make_dynamic_instructions(MAIN_AGENT_INSTRUCTIONS, project_context)

    async with AsyncExitStack() as stack:
        mcp_servers = await build_mcp_servers(stack, mcp_config_path)
        coordinator_tools, specialist_agent_defs = classify_specialist_tools(main_tools)

        def build_specialist_model_settings(agent_name: str) -> ModelSettings:
            profile = SPECIALIST_MODEL_PROFILES.get(agent_name, {})
            if not profile:
                return global_ms
            return global_ms.resolve(ModelSettings(**profile))

        # Schematic Agent
        schematic_agent = Agent(
            name="schematicAgent",
            instructions=SCHEMATIC_AGENT_INSTRUCTIONS,
            model=model,
            model_settings=build_specialist_model_settings("schematicAgent"),
            tools=[create_bridge_tool(tool) for tool in schematic_tools],
            mcp_servers=mcp_servers,
            handoff_description="Specialist for schematic, pin map, and hardware wiring tasks.",
            input_guardrails=[secret_request_guardrail],
            output_guardrails=[secret_output_guardrail],
            hooks=hooks,
            output_type=SPECIALIST_RESULT_TYPE,
        )

        # Built-in sub-agent wrappers
        builtin_wrapped_agents = []
        for agent_def in built_in_agents:
            delegate_tool = create_builtin_subagent_tool(agent_def)
            builtin_agent = Agent(
                name=f"Builtin::{agent_def.get('displayName') or agent_def.get('name')}",
                instructions=(
                    f"You are a wrapper around the application's builtin agent "
                    f"{agent_def.get('displayName') or agent_def.get('name')}. "
                    f"{agent_def.get('description') or ''} "
                    f"Always use your delegate tool to complete work in this domain."
                ),
                model=model,
                model_settings=global_ms,
                tools=[delegate_tool],
                handoff_description=agent_def.get("description") or agent_def.get("displayName") or agent_def.get("name") or "Builtin agent",
                input_guardrails=[secret_request_guardrail],
                output_guardrails=[secret_output_guardrail],
                hooks=hooks,
            )
            builtin_wrapped_agents.append(builtin_agent)

        # Specialist Agents with structured output + StopAtTools
        specialist_agents = []
        for agent_def in specialist_agent_defs:
            specialist_per_tool_limits = {"get_errors": 1}
            if agent_def["name"] == "ProjectSpecialist":
                specialist_per_tool_limits.update({
                    "ask_user": 2, "create_project": 2, "switch_board": 2,
                    "set_board_config": 2, "build_project": 2,
                })
            specialist_budget = ToolBudgetTracker(
                name=agent_def["name"],
                max_total_calls=agent_def.get("max_tool_calls", 3),
                default_tool_limit=1,
                per_tool_limits=specialist_per_tool_limits,
            )
            # Determine stop_at tools for specialist
            stop_tools: list[str] | None = None
            if agent_def["name"] in {"FileSpecialist", "TerminalSpecialist"}:
                stop_tools = ["create_file", "edit_file", "replace_string_in_file",
                              "execute_command", "start_background_command"]

            agent_tools = [
                create_bridge_tool(
                    tool,
                    budget_trackers=[GLOBAL_TOOL_BUDGETS, specialist_budget],
                    agent_name=agent_def["name"],
                )
                for tool in agent_def["tools"]
            ]

            # Give ResearchSpecialist access to web search if available
            if agent_def["name"] == "ResearchSpecialist" and web_search_tool:
                agent_tools.append(web_search_tool)

            # When StopAtTools is active, output_type is ignored (agent returns tool output
            # directly, not LLM-generated structured output). Remove it to avoid confusion.
            effective_output_type = None if stop_tools else agent_def.get("output_type")

            specialist_agents.append(
                Agent(
                    name=agent_def["name"],
                    instructions=agent_def["instructions"],
                    model=model,
                    model_settings=build_specialist_model_settings(agent_def["name"]),
                    tools=agent_tools,
                    mcp_servers=mcp_servers,
                    handoff_description=agent_def["description"],
                    input_guardrails=[secret_request_guardrail],
                    output_guardrails=[secret_output_guardrail],
                    hooks=hooks,
                    output_type=effective_output_type,
                    tool_use_behavior=StopAtTools(stop_at=stop_tools) if stop_tools else "run_llm_again",
                )
            )

        # Main Agent — all features combined
        all_main_tools = [
            *[create_bridge_tool(tool) for tool in coordinator_tools],
            schematic_agent.as_tool(
                tool_name="delegate_to_schematicAgent",
                tool_description="Delegate schematic, wiring, pin map, or board connection tasks to the schematic specialist.",
                needs_approval=True,
                session=session,
            ),
            *[
                agent.as_tool(
                    tool_name=f"delegate_to_{sanitize_tool_suffix(agent.name)}",
                    tool_description=agent.handoff_description or f"Delegate to {agent.name}",
                    needs_approval=True,
                    session=session,
                )
                for agent in specialist_agents
            ],
            *[
                agent.as_tool(
                    tool_name=f"delegate_to_builtin_{sanitize_tool_suffix(agent.name)}",
                    tool_description=agent.handoff_description or f"Delegate to {agent.name}",
                    needs_approval=True,
                    session=session,
                )
                for agent in builtin_wrapped_agents
            ],
            *hosted_tools,
        ]

        main_agent = Agent(
            name="AilyOpenAIAgentsMain",
            instructions=dynamic_instructions,
            model=model,
            model_settings=global_ms,
            tools=all_main_tools,
            handoffs=[schematic_agent, *specialist_agents, *builtin_wrapped_agents],
            mcp_servers=mcp_servers,
            input_guardrails=[secret_request_guardrail],
            output_guardrails=[secret_output_guardrail],
            hooks=hooks,
            prompt=prompt_ref,
        )

        # Build RunConfig with all global settings
        # Guardrails are set per-agent to avoid duplicate execution.
        run_config = RunConfig(
            model=model,
            model_provider=multi_provider,
            model_settings=global_ms,
            handoff_input_filter=None,
            nest_handoff_history=True,
            workflow_name="AilyOpenAIAgentsTurn",
            trace_id=gen_trace_id() if tracing_enabled else None,
            trace_metadata={"session_id": session_id},
            tracing_disabled=not tracing_enabled,
            call_model_input_filter=context_trimming_filter,
            tool_error_formatter=None,
        )

        trace_id = run_config.trace_id
        if trace_id:
            emit({"type": "trace_info", "trace_id": trace_id, "trace_url": build_trace_url(trace_id)})

        async def execute() -> str:
            state = await load_run_state(run_state_path, main_agent)
            current_input: Any = state if state is not None else user_input

            while True:
                result = await stream_single_run(main_agent, current_input, session, max_turns, run_config)

                if result.interruptions:
                    state = result.to_state()
                    save_run_state(run_state_path, state)

                    for interruption in result.interruptions:
                        emit({
                            "type": "approval_request",
                            "call_id": interruption.call_id or f"approval_{uuid.uuid4().hex}",
                            "tool_name": interruption.name or "unknown_tool",
                            "tool_args": interruption.arguments or "{}",
                        })
                        decision = await asyncio.to_thread(read_stdin_event, "approval_result", interruption.call_id)
                        if decision.get("approved"):
                            state.approve(interruption)
                        else:
                            state.reject(interruption, rejection_message=decision.get("reason") or "User rejected tool execution")

                    save_run_state(run_state_path, state)
                    current_input = state
                    continue

                clear_run_state(run_state_path)

                # Emit final hook metrics
                all_metrics = hooks.get_all_metrics()
                if all_metrics:
                    emit({"type": "hook_metrics", "metrics": all_metrics})

                final_output = result.final_output
                if isinstance(final_output, str):
                    return final_output
                return json.dumps(final_output, ensure_ascii=False, indent=2)

        try:
            if trace_id:
                with trace("AilyOpenAIAgentsTurn", trace_id=trace_id):
                    return await execute()
            return await execute()
        except InputGuardrailTripwireTriggered as exc:
            emit({"type": "guardrail_tripwire", "guardrail_kind": "input", "info": str(exc)})
            raise RuntimeError("Input guardrail triggered")
        except OutputGuardrailTripwireTriggered as exc:
            emit({"type": "guardrail_tripwire", "guardrail_kind": "output", "info": str(exc)})
            raise RuntimeError("Output guardrail triggered")
        except ToolInputGuardrailTripwireTriggered as exc:
            emit({"type": "guardrail_tripwire", "guardrail_kind": "tool_input", "info": str(exc)})
            raise RuntimeError("Tool input guardrail triggered")
        except MaxTurnsExceeded as exc:
            emit({"type": "max_turns_exceeded", "info": str(exc)})
            raise RuntimeError(f"Max turns exceeded: {exc}")
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Simple Runner Mode (merged from openai_agents_runner.py)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a pragmatic software engineering assistant. "
    "Follow the user prompt exactly, respond in plain text, and keep the answer concise."
)


def load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def format_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


async def run_simple(request: dict) -> str:
    """Simple one-shot runner — no tools, no handoffs, no guardrails."""
    model_config = request.get("modelConfig") or {}
    prompt = request.get("prompt") or request.get("userInput") or ""
    instructions = request.get("instructions") or SYSTEM_PROMPT
    prompt_cfg = request.get("prompt")

    if not prompt.strip():
        raise RuntimeError("Missing prompt content.")

    api_key, base_url, model_name = resolve_model_config(model_config)
    set_tracing_disabled(True)

    client = AsyncOpenAI(api_key=api_key, base_url=base_url or None)
    use_responses = should_use_responses_api(base_url)

    if use_responses:
        model = OpenAIResponsesModel(model=model_name, openai_client=client)
    else:
        model = OpenAIChatCompletionsModel(model=model_name, openai_client=client)

    prompt_ref = None
    if prompt_cfg and isinstance(prompt_cfg, dict) and prompt_cfg.get("id"):
        prompt_ref = Prompt(
            id=prompt_cfg["id"],
            version=prompt_cfg.get("version"),
            variables=prompt_cfg.get("variables") or {},
        )

    agent = Agent(
        name="AilyOpenAIAgents",
        instructions=instructions,
        model=model,
        prompt=prompt_ref,
    )

    result = await Runner.run_async(agent, prompt)
    return format_output(result.final_output)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="OpenAI Agents SDK unified runner for qingxinyuma")
    parser.add_argument("--request-file", required=True, help="Path to JSON request file")
    parser.add_argument("--mode", choices=["turn", "simple"], default="turn",
                        help="Runner mode: 'turn' for full-featured, 'simple' for one-shot")
    args = parser.parse_args()

    try:
        request = load_json(args.request_file)

        if args.mode == "simple":
            final_output = asyncio.run(run_simple(request))
        else:
            final_output = asyncio.run(run_turn(request))

        if final_output:
            emit({"type": "ModelClientStreamingChunkEvent", "content": final_output})
        emit({"type": "TaskCompleted", "stop_reason": "COMPLETED"})
        return 0
    except Exception as exc:
        emit({"type": "error", "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
