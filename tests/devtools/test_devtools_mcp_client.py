# -*- coding: utf-8 -*-

from agent_app.devtools.mcp_client import (
    list_tools,
)
from agent_app.devtools.mcp_client import (
    call_tool,
)
from agent_app.devtools.mcp_client import main

import json

import httpx
import pytest


def test_list_tools(mcp_url):
    assert sorted(list_tools(mcp_url)) == [
        "get_agent",
        "get_org_context",
        "get_session",
        "list_agents",
        "list_policies",
        "list_sessions",
        "list_tool_definitions",
        "search_tool_calls",
    ]


def test_call_tool(mcp_url):
    session = call_tool(mcp_url, "get_session", {"session_id": "ses_001"})
    assert session["task"] == "Resolve ticket TCK-1"
    agents = call_tool(mcp_url, "list_agents", {"role": "coding"})
    assert agents["total"] == 1
    assert [row["agent_id"] for row in agents["agents"]] == ["agt_b2"]
    with pytest.raises(RuntimeError, match="session 'ses_999' not found"):
        call_tool(mcp_url, "get_session", {"session_id": "ses_999"})


class CountingAuth(httpx.Auth):
    """Stands in for SigV4: marks and counts every request it sees."""

    def __init__(self):
        self.count = 0

    def auth_flow(self, request):
        self.count += 1
        request.headers["X-Signed"] = "yes"
        yield request


def test_auth(mcp_url):
    """Every request goes through the auth, as SigV4 would sign it."""
    auth = CountingAuth()
    assert "get_session" in list_tools(mcp_url, auth=auth)
    session = call_tool(mcp_url, "get_session", {"session_id": "ses_001"}, auth=auth)
    assert session["session_id"] == "ses_001"
    assert auth.count >= 4  # initialize and the call, for each session


def test_main(mcp_url, capsys):
    args = ["--url", mcp_url, "--tool", "get_session"]
    assert main(args + ["--arguments", json.dumps({"session_id": "ses_001"})]) == 0
    out = capsys.readouterr().out
    assert "tool: get_session" in out
    assert '"task": "Resolve ticket TCK-1"' in out
    assert main(args + ["--arguments", json.dumps({"session_id": "ses_999"})]) == 1
    assert "error: " in capsys.readouterr().out


def test_main_url_from_env(mcp_url, monkeypatch, capsys):
    monkeypatch.setenv("MCP_URL", mcp_url)
    assert main(["--tool", "list_policies"]) == 0
    assert f"MCP server: {mcp_url}" in capsys.readouterr().out


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.devtools.mcp_client",
        preview=False,
    )
