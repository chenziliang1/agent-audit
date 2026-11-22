# -*- coding: utf-8 -*-

from agent_app.devtools.local_run import (
    get_local_url,
)
from agent_app.devtools.local_run import (
    get_mcp_url_env,
)
from agent_app.devtools.local_run import (
    get_local_command,
)
from agent_app.devtools.local_run import (
    get_dev_command,
)
from agent_app.devtools.local_run import (
    get_call_args,
)
from agent_app.devtools.local_run import serve
from agent_app.devtools.local_run import run
from agent_app.devtools.local_run import main

import sys

import pytest

from agent_app.config.api import Config
from agent_app.devtools import local_run
from agent_app.devtools.local_port import (
    PortHeldByOtherError,
)
from agent_app.agentcore_project.registry import (
    get_runtime_specs,
)

PKG = "agent_app"


@pytest.fixture
def specs(config: Config):
    by_name = {spec.name: spec for spec in get_runtime_specs(config)}
    return by_name["AuditMcp"], by_name["AuditAgent"]


@pytest.fixture
def executed(monkeypatch):
    """Record what serve() would exec, and free no port."""
    calls = []
    monkeypatch.setattr(local_run, "free_port", lambda port: [])
    monkeypatch.setattr(
        local_run.os, "execvpe", lambda file, argv, env: calls.append((argv, env))
    )
    return calls


def test_urls(specs):
    mcp, agent = specs
    assert get_local_url(mcp) == "http://localhost:18733/mcp"
    assert get_local_url(agent) == "http://localhost:18734"
    assert get_mcp_url_env(agent, list(specs)) == {
        "MCP_URL_AUDITMCP": "http://localhost:18733/mcp"
    }
    assert get_mcp_url_env(mcp, list(specs)) == {}


def test_get_local_command(specs):
    mcp, agent = specs
    env, argv = get_local_command(mcp, list(specs))
    assert env == {"FASTMCP_PORT": "18733"}
    assert argv == [sys.executable, "-m", f"{PKG}.runtimes.audit_mcp"]
    env, argv = get_local_command(agent, list(specs))
    assert env == {"MCP_URL_AUDITMCP": "http://localhost:18733/mcp"}
    assert argv[2:] == [
        "uvicorn",
        f"{PKG}.runtimes.audit_agent:app",
        "--host",
        "127.0.0.1",
        "--port",
        "18734",
    ]


def test_get_dev_command(specs, config: Config):
    """The region of the config, an explicit port, and the agent's MCP URLs."""
    mcp, agent = specs
    env, argv = get_dev_command(agent, list(specs), config)
    assert env == {
        "AWS_REGION": "us-east-1",
        "MCP_URL_AUDITMCP": "http://localhost:18733/mcp",
    }
    assert argv == [
        "agentcore",
        "dev",
        "--agent",
        "AuditAgent",
        "--no-traces",
        "--port",
        "18734",
    ]


def test_get_call_args(specs):
    mcp, agent = specs
    assert get_call_args(mcp) == [
        "--url",
        "http://localhost:18733/mcp",
        "--tool",
        "list_sessions",
        "--arguments",
        '{"limit": 3}',
    ]
    args = get_call_args(agent)
    assert args[:3] == ["--url", "http://localhost:18734", "--prompt"]


def test_serve(executed, monkeypatch, capsys):
    monkeypatch.setenv("KEEP_ME", "1")
    assert serve({"A": "b"}, ["prog", "--x"], port=18799) == 0
    ((argv, env),) = executed
    assert argv == ["prog", "--x"]
    assert env["A"] == "b" and env["KEEP_ME"] == "1"
    assert "A=b" in capsys.readouterr().out
    monkeypatch.setattr(local_run, "free_port", lambda port: [123])
    serve({}, ["prog"], port=18799)
    assert "stopped [123]" in capsys.readouterr().out


def test_serve_port_held_by_other(monkeypatch, capsys):
    def held(port):
        raise PortHeldByOtherError("held by someone else")

    monkeypatch.setattr(local_run, "free_port", held)
    assert serve({}, ["prog"], port=18799) == 1
    assert "held by someone else" in capsys.readouterr().out


def test_run(executed, config: Config, monkeypatch):
    assert run("AuditMcp", "local", config) == 0
    assert run("AuditAgent", "dev", config) == 0
    assert executed[0][0][-1] == f"{PKG}.runtimes.audit_mcp"
    assert executed[1][0][:2] == ["agentcore", "dev"]
    calls = []
    monkeypatch.setattr(
        local_run.mcp_client, "main", lambda args: calls.append(args) or 0
    )
    monkeypatch.setattr(
        local_run.agent_client, "main", lambda args: calls.append(args) or 0
    )
    assert run("AuditMcp", "call", config) == 0
    assert run("AuditAgent", "call", config) == 0
    assert "--tool" in calls[0] and "--prompt" in calls[1]
    with pytest.raises(ValueError, match="no runtime 'Missing'"):
        run("Missing", "local", config)


def test_main(executed):
    assert main(["--runtime", "AuditMcp", "--mode", "local"]) == 0
    assert executed[0][1]["FASTMCP_PORT"] == "18733"


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.devtools.local_run",
        preview=False,
    )
