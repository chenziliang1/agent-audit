# -*- coding: utf-8 -*-

from agent_app.runtimes.audit_mcp import mcp
from agent_app.runtimes.audit_mcp import main

import pytest

import json
import asyncio

from mcp.server.fastmcp.exceptions import ToolError

from agent_app.config.api import Config
from agent_app.one.api import one
from agent_app.audit import queries


@pytest.fixture(autouse=True)
def sample_store(monkeypatch, audit_store):
    """
    Serve the fictional sample instead of the bundled dataset: ``one`` caches
    its store in the instance, so that is where the sample goes.
    """
    monkeypatch.setitem(one.__dict__, "audit_store", audit_store)


def test_name(config: Config):
    """The server is named after the runtime in agentcore.json."""
    assert mcp.name == config.agentcore_runtime_name_audit_mcp


def test_list_tools():
    tools = asyncio.run(mcp.list_tools())
    names = sorted(tool.name for tool in tools)
    assert names == [
        "get_agent",
        "get_org_context",
        "get_session",
        "list_agents",
        "list_policies",
        "list_sessions",
        "list_tool_definitions",
        "search_tool_calls",
    ]
    for tool in tools:
        # the description is the query's docstring; the store is not a parameter
        assert tool.description.strip() == getattr(queries, tool.name).__doc__.strip()
        assert "store" not in tool.inputSchema["properties"]
        # the output schema comes from the Pydantic return type
        assert tool.outputSchema is not None


@pytest.mark.parametrize(
    "name, arguments, key, expected",
    [
        ("list_policies", {}, "policy_id", ["P-01", "P-02"]),
        ("list_tool_definitions", {"side_effect": "read"}, "name", ["ticket.get"]),
    ],
)
def test_call_list_tool(name, arguments, key, expected):
    """
    A list tool reaches its query through one.audit_store; FastMCP wraps a
    list result in the structured output, ``{"result": [...]}``.
    """
    _, structured = asyncio.run(mcp.call_tool(name, arguments))
    assert [row[key] for row in structured["result"]] == expected


def test_call_tool_get_org_context():
    _, org = asyncio.run(mcp.call_tool("get_org_context", {}))
    assert org["company"] == "Acme Corp"


def test_call_tool_list_agents():
    """
    The agents come with their count, as an object, not as a bare list.
    """
    _, listed = asyncio.run(mcp.call_tool("list_agents", {"role": "coding"}))
    assert listed["total"] == 1
    assert [row["agent_id"] for row in listed["agents"]] == ["agt_b2"]


def test_call_tool_get_agent():
    _, agent = asyncio.run(mcp.call_tool("get_agent", {"agent_id": "agt_b2"}))
    assert agent["allowed_tools"] == ["shell.exec", "git.push"]


def test_call_tool_list_sessions():
    arguments = {"agent_id": "agt_a1", "limit": 1, "offset": 1}
    _, page = asyncio.run(mcp.call_tool("list_sessions", arguments))
    assert page["total"] == 2
    assert [row["session_id"] for row in page["sessions"]] == ["ses_002"]
    arguments = {
        "status": "completed",
        "tool": "git.push",
        "started_from": "2026-01-01",
        "started_before": "2026-02-01",
    }
    _, page = asyncio.run(mcp.call_tool("list_sessions", arguments))
    assert [row["session_id"] for row in page["sessions"]] == ["ses_003"]


def test_call_tool_get_session():
    """
    A tool call goes through the MCP layer and returns the model both as JSON
    text (for clients that read only text) and as structured output.
    """
    arguments = {"session_id": "ses_001"}
    content, session = asyncio.run(mcp.call_tool("get_session", arguments))
    assert json.loads(content[0].text) == session
    assert session["task"] == "Resolve ticket TCK-1"
    assert [call["tool"] for call in session["tool_calls"]] == [
        "ticket.get",
        "payments.refund",
    ]
    assert session["tool_calls"][0]["approval"] is None
    assert session["tool_calls"][1]["approval"]["change_ticket"] == "CHG-1"


def test_call_tool_search_tool_calls():
    arguments = {"tool": "shell.exec", "status": "denied", "text": "| sh"}
    _, page = asyncio.run(mcp.call_tool("search_tool_calls", arguments))
    assert page["total"] == 1
    assert page["calls"][0]["session_id"] == "ses_003"
    assert page["calls"][0]["call"]["call_id"] == "call_4"
    arguments = {"agent_id": "agt_a1", "limit": 1, "offset": 2}
    _, page = asyncio.run(mcp.call_tool("search_tool_calls", arguments))
    assert [row["call"]["call_id"] for row in page["calls"]] == ["call_3"]


def test_call_tool_errors():
    with pytest.raises(ToolError, match="session 'ses_999' not found"):
        asyncio.run(mcp.call_tool("get_session", {"session_id": "ses_999"}))
    with pytest.raises(ToolError, match="agent 'agt_zz' not found"):
        asyncio.run(mcp.call_tool("get_agent", {"agent_id": "agt_zz"}))
    with pytest.raises(ToolError, match="limit must be between 1 and 100"):
        asyncio.run(mcp.call_tool("list_sessions", {"limit": 500}))
    # A name where an ID belongs: the error tells the model the ID.
    with pytest.raises(ToolError, match="whose agent_id is 'agt_a1'"):
        asyncio.run(mcp.call_tool("list_sessions", {"agent_id": "widget-helper-01"}))


def test_no_tool_result_carries_a_label():
    """
    Nothing a tool returns has a ground-truth field name in it, at any depth
    of the output schema.
    """
    forbidden = {
        "risky",
        "scenario",
        "kind",
        "hard_negative",
        "max_severity",
        "severity",
        "categories",
        "policy_ids",
        "risky_call_ids",
        "evidence_call_ids",
        "hard_negative_call_ids",
        "multi_step",
        "explanation",
        "summary",
    }

    def property_names(schema) -> set[str]:
        names = set()
        if isinstance(schema, dict):
            names |= set(schema.get("properties", {}))
            for value in schema.values():
                names |= property_names(value)
        elif isinstance(schema, list):
            for value in schema:
                names |= property_names(value)
        return names

    for tool in asyncio.run(mcp.list_tools()):
        assert not property_names(tool.outputSchema) & forbidden, tool.name


def test_main(monkeypatch, capsys):
    """main() loads the config and the audit data, then serves."""
    calls = []
    monkeypatch.setattr(mcp, "run", lambda transport: calls.append(transport))
    main()
    assert calls == ["streamable-http"]
    out = capsys.readouterr().out
    assert "Loaded the config of 'dev' on runtime 'local'" in out
    assert "Loaded the audit data: 2 agents, 3 sessions, 5 tool calls" in out


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.runtimes.audit_mcp",
        preview=False,
    )
