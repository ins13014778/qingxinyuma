import argparse
import asyncio
import json
import os
import re
import sys
import uuid
from collections import defaultdict
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from openai.types.responses import ResponseFunctionCallArgumentsDeltaEvent, ResponseTextDeltaEvent

from agents import (
    Agent,
    FunctionTool,
    GuardrailFunctionOutput,
    OpenAIChatCompletionsModel,
    InputGuardrailTripwireTriggered,
    OpenAIResponsesModel,
    OutputGuardrailTripwireTriggered,
    RunContextWrapper,
    RunState,
    Runner,
    SQLiteSession,
    input_guardrail,
    output_guardrail,
    gen_trace_id,
    set_tracing_disabled,
    set_tracing_export_api_key,
    trace,
)
from agents.mcp import MCPServerStdio


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
        "matcher": lambda name: name in {
            "create_project",
            "build_project",
            "reload_project",
            "switch_board",
            "get_board_config",
            "set_board_config",
            "save_arch",
            "clone_repository",
            "get_errors",
            "memory",
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
        "matcher": lambda name: name in {
            "read_file",
            "create_file",
            "edit_file",
            "replace_string_in_file",
            "multi_replace_string_in_file",
            "delete_file",
            "delete_folder",
            "create_folder",
            "list_directory",
            "get_directory_tree",
            "grep_tool",
            "glob_tool",
            "get_context",
            "get_project_info",
            "get_project_context",
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
        "matcher": lambda name: name in {
            "execute_command",
            "start_background_command",
            "get_terminal_output",
        },
    },
    {
        "key": "blockly",
        "name": "BlocklySpecialist",
        "instructions": (
            "You specialize in Blockly, ABS syntax, library block analysis, DSL block generation, and code generation diagnostics."
        ),
        "matcher": lambda name: name in {
            "analyze_library_blocks",
            "get_abs_syntax",
            "verify_block_existence",
            "dsl_create_blocks",
            "arduino_syntax_check",
        },
    },
    {
        "key": "research",
        "name": "ResearchSpecialist",
        "instructions": (
            "You specialize in searching available tools, loading skills, fetching remote content, and hardware/library discovery."
        ),
        "matcher": lambda name: name in {
            "search_available_tools",
            "load_skill",
            "fetch",
            "search_boards_libraries",
            "get_component_catalog",
            "get_pinmap_summary",
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
}
GET_ERRORS_FAST_DEGRADE_MESSAGE = (
    "get_errors failed or diagnostics are currently unavailable. "
    "Do not retry get_errors in this run. "
    "Return a concise risk summary based on the project structure, board config, and any evidence already collected."
)


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
        emit(
            {
                "type": "tool_call_request",
                "tool_id": tool_id,
                "tool_name": "run_subagent",
                "tool_args": json.dumps(
                    {
                        "agent": agent_name,
                        **(json.loads(args_json or "{}")),
                    },
                    ensure_ascii=False,
                ),
            }
        )
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
        agents.append(
            {
                "name": specialist["name"],
                "instructions": specialist["instructions"],
                "tools": tools,
                "description": specialist["instructions"],
                "max_tool_calls": 4 if specialist["name"] == "ProjectSpecialist" else SPECIALIST_FIRST_ROUND_MAX_TOOL_CALLS if specialist["name"] in {
                    "ProjectSpecialist",
                    "FileSpecialist",
                    "TerminalSpecialist",
                } else 3,
            }
        )

    return coordinator_tools, agents


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


async def stream_single_run(main_agent: Agent[Any], input_data: Any, session: SQLiteSession | None):
    result = Runner.run_streamed(main_agent, input_data, session=session) if not isinstance(input_data, RunState) else Runner.run_streamed(main_agent, input_data)
    async for event in result.stream_events():
        if event.type == "raw_response_event":
            raw = event.data
            emit({"type": "raw_response_event", "event_type": getattr(raw, "type", "unknown")})
            if isinstance(raw, ResponseTextDeltaEvent):
                emit({"type": "ModelClientStreamingChunkEvent", "content": raw.delta})
            elif isinstance(raw, ResponseFunctionCallArgumentsDeltaEvent):
                emit(
                    {
                        "type": "function_call_arguments_delta",
                        "call_id": getattr(raw, "item_id", None) or getattr(raw, "output_index", None),
                        "delta": raw.delta,
                    }
                )
        elif event.type == "run_item_stream_event":
            emit({"type": "run_item_stream_event", "name": event.name, "item_type": getattr(event.item, "type", "unknown")})
        elif event.type == "agent_updated_stream_event":
            emit({"type": "agent_updated_stream_event", "agent_name": event.new_agent.name})
    return result


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
    })
    if use_responses_api:
        model = OpenAIResponsesModel(model=model_name, openai_client=client)
    else:
        model = OpenAIChatCompletionsModel(model=model_name, openai_client=client)

    if session_db_path != ":memory:":
        ensure_parent_dir(session_db_path)
    session = SQLiteSession(session_id, db_path=session_db_path)

    async with AsyncExitStack() as stack:
        mcp_servers = await build_mcp_servers(stack, mcp_config_path)
        coordinator_tools, specialist_agent_defs = classify_specialist_tools(main_tools)

        schematic_agent = Agent(
            name="SchematicAgent",
            instructions=SCHEMATIC_AGENT_INSTRUCTIONS,
            model=model,
            tools=[create_bridge_tool(tool) for tool in schematic_tools],
            mcp_servers=mcp_servers,
            handoff_description="Specialist for schematic, pin map, and hardware wiring tasks.",
            input_guardrails=[secret_request_guardrail],
            output_guardrails=[secret_output_guardrail],
        )

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
                tools=[delegate_tool],
                handoff_description=agent_def.get("description") or agent_def.get("displayName") or agent_def.get("name") or "Builtin agent",
                input_guardrails=[secret_request_guardrail],
                output_guardrails=[secret_output_guardrail],
            )
            builtin_wrapped_agents.append(builtin_agent)

        specialist_agents = []
        for agent_def in specialist_agent_defs:
            specialist_per_tool_limits = {"get_errors": 1}
            if agent_def["name"] == "ProjectSpecialist":
                specialist_per_tool_limits.update({
                    "ask_user": 2,
                    "create_project": 2,
                    "switch_board": 2,
                    "set_board_config": 2,
                    "build_project": 2,
                })
            specialist_budget = ToolBudgetTracker(
                name=agent_def["name"],
                max_total_calls=agent_def.get("max_tool_calls", 3),
                default_tool_limit=1,
                per_tool_limits=specialist_per_tool_limits,
            )
            specialist_agents.append(
                Agent(
                    name=agent_def["name"],
                    instructions=agent_def["instructions"],
                    model=model,
                    tools=[
                        create_bridge_tool(
                            tool,
                            budget_trackers=[GLOBAL_TOOL_BUDGETS, specialist_budget],
                            agent_name=agent_def["name"],
                        )
                        for tool in agent_def["tools"]
                    ],
                    mcp_servers=mcp_servers,
                    handoff_description=agent_def["description"],
                    input_guardrails=[secret_request_guardrail],
                    output_guardrails=[secret_output_guardrail],
                )
            )

        main_agent = Agent(
            name="AilyOpenAIAgentsMain",
            instructions=request.get("mainAgentInstructions") or MAIN_AGENT_INSTRUCTIONS,
            model=model,
            tools=[
                *[create_bridge_tool(tool) for tool in coordinator_tools],
                schematic_agent.as_tool(
                    tool_name="delegate_to_schematic_agent",
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
            ],
            handoffs=[schematic_agent, *specialist_agents, *builtin_wrapped_agents],
            mcp_servers=mcp_servers,
            input_guardrails=[secret_request_guardrail],
            output_guardrails=[secret_output_guardrail],
        )

        trace_id = gen_trace_id() if tracing_enabled else None
        if trace_id:
            emit({"type": "trace_info", "trace_id": trace_id, "trace_url": build_trace_url(trace_id)})

        async def execute() -> str:
            state = await load_run_state(run_state_path, main_agent)
            current_input: Any = state if state is not None else user_input

            while True:
                result = await stream_single_run(main_agent, current_input, session)

                if result.interruptions:
                    state = result.to_state()
                    save_run_state(run_state_path, state)

                    for interruption in result.interruptions:
                        emit(
                            {
                                "type": "approval_request",
                                "call_id": interruption.call_id or f"approval_{uuid.uuid4().hex}",
                                "tool_name": interruption.name or "unknown_tool",
                                "tool_args": interruption.arguments or "{}",
                            }
                        )
                        decision = await asyncio.to_thread(read_stdin_event, "approval_result", interruption.call_id)
                        if decision.get("approved"):
                            state.approve(interruption)
                        else:
                            state.reject(interruption, rejection_message=decision.get("reason") or "User rejected tool execution")

                    save_run_state(run_state_path, state)
                    current_input = state
                    continue

                clear_run_state(run_state_path)

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
        finally:
            session.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-file", required=True)
    args = parser.parse_args()

    try:
        request = load_json(args.request_file)
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
