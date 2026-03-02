#!/usr/bin/env python3
"""orchestrator_sdk_spike.py — replace subprocess claude -p with Agent SDK query().

Requires: uv add claude-agent-sdk (v0.1.44+, bundles Claude CLI 2.1.59)

The SDK is a WRAPPER around the Claude CLI subprocess. Under the hood,
SubprocessCLITransport spawns:
  claude --output-format stream-json --verbose --input-format stream-json ...

Key insight: query() is async (anyio). The orchestrator is sync.
This spike uses anyio.run() to bridge.

Key gotcha: setting_sources=None (default) means NO CLAUDE.md, NO hooks,
NO skills loaded. Must explicitly pass ["user", "project"] to replicate
current claude -p behavior.
"""

import os
from dataclasses import dataclass
from typing import Any

import anyio

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)


@dataclass
class TaskResult:
    """Mirrors what the current orchestrator extracts from claude -p --output-format json."""

    status: str  # "done" | "done_with_denials" | "failed"
    cost_usd: float
    tokens_in: int
    tokens_out: int
    result_text: str
    session_id: str
    duration_ms: int
    duration_api_ms: int
    num_turns: int
    is_error: bool
    model: str | None
    error: str | None
    usage: dict | None
    structured_output: Any


async def run_task(
    prompt: str,
    *,
    project: str = "meta",
    cwd: str | None = None,
    model: str | None = None,
    max_turns: int = 15,
    max_budget_usd: float = 5.0,
    allowed_tools: list[str] | None = None,
    effort: str | None = None,  # "low" | "medium" | "high" | "max"
    setting_sources: list[str] | None = None,
    permission_mode: str = "acceptEdits",
) -> TaskResult:
    """Drop-in replacement for run_claude_task() in orchestrator.py."""
    resolved_cwd = cwd or os.path.expanduser(f"~/Projects/{project}")

    options = ClaudeAgentOptions(
        model=model,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        permission_mode=permission_mode,
        cwd=resolved_cwd,
        effort=effort,
        allowed_tools=allowed_tools or [],
        setting_sources=setting_sources,
        fallback_model="sonnet",
        system_prompt={"type": "preset", "preset": "claude_code"},
        env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"},
    )

    text_parts: list[str] = []
    result_msg: ResultMessage | None = None
    last_model: str | None = None

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            last_model = message.model
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
        elif isinstance(message, ResultMessage):
            result_msg = message

    if result_msg is None:
        return TaskResult(
            status="failed",
            cost_usd=0,
            tokens_in=0,
            tokens_out=0,
            result_text="",
            session_id="",
            duration_ms=0,
            duration_api_ms=0,
            num_turns=0,
            is_error=True,
            model=last_model,
            error="No ResultMessage received from SDK",
            usage=None,
            structured_output=None,
        )

    usage = result_msg.usage or {}
    tokens_in = sum(
        v.get("inputTokens", 0) + v.get("cacheReadInputTokens", 0)
        for v in usage.values()
        if isinstance(v, dict)
    )
    tokens_out = sum(
        v.get("outputTokens", 0) for v in usage.values() if isinstance(v, dict)
    )

    return TaskResult(
        status="done" if not result_msg.is_error else "failed",
        cost_usd=result_msg.total_cost_usd or 0.0,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        result_text=result_msg.result or "\n".join(text_parts),
        session_id=result_msg.session_id,
        duration_ms=result_msg.duration_ms,
        duration_api_ms=result_msg.duration_api_ms,
        num_turns=result_msg.num_turns,
        is_error=result_msg.is_error,
        model=last_model,
        error=None
        if not result_msg.is_error
        else (result_msg.result or "Unknown error"),
        usage=usage,
        structured_output=result_msg.structured_output,
    )


def run_claude_task_sdk(task: dict, cwd: str) -> TaskResult:
    """Sync wrapper. Drop-in replacement for orchestrator.py's run_claude_task()."""
    return anyio.run(
        run_task,
        task["prompt"],
        project=task.get("project", "meta"),
        cwd=cwd,
        model=task.get("model"),
        max_turns=task.get("max_turns") or 15,
        max_budget_usd=task.get("max_budget_usd") or 5.0,
        allowed_tools=task.get("allowed_tools", "").split(",")
        if task.get("allowed_tools")
        else None,
        effort=task.get("effort"),
        setting_sources=["user", "project"],
        permission_mode="acceptEdits",
    )


async def _test():
    """Standalone test: ask a simple question with minimal cost."""
    result = await run_task(
        "What is 2 + 2? Reply with just the number.",
        max_turns=1,
        max_budget_usd=0.10,
        effort="low",
        setting_sources=None,
    )
    print(f"Status:     {result.status}")
    print(f"Cost:       ${result.cost_usd:.4f}")
    print(f"Tokens:     {result.tokens_in} in / {result.tokens_out} out")
    print(f"Duration:   {result.duration_ms}ms (API: {result.duration_api_ms}ms)")
    print(f"Turns:      {result.num_turns}")
    print(f"Session:    {result.session_id}")
    print(f"Model:      {result.model}")
    print(f"Result:     {result.result_text[:200]}")


if __name__ == "__main__":
    anyio.run(_test)
