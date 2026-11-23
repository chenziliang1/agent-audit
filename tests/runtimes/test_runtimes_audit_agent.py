# -*- coding: utf-8 -*-

from agent_app.runtimes.audit_agent import make_record_verdict_tool
from agent_app.runtimes.audit_agent import make_agent
from agent_app.runtimes.audit_agent import build_agent
from agent_app.runtimes.audit_agent import verdict_log
from agent_app.runtimes.audit_agent import model_log
from agent_app.runtimes.audit_agent import app
from agent_app.runtimes.audit_agent import invoke
from agent_app.runtimes.audit_agent import main

import pytest
from starlette.exceptions import HTTPException

from agent_app.one.api import one
from agent_app.tests import FakeAgentResult
from agent_app.config.api import Config
from agent_app.audit import audit_agent as definition
from agent_app.audit.audit_agent import VerdictLog
from agent_app.audit.audit_agent import ModelLog
from agent_app.runtimes import audit_agent
from agent_app.runtimes.common import ProcessAgent
from agent_app.runtimes.mcp_connection import get_runtime_arn_env_var

TOOL_NAMES = [
    "get_agent",
    "get_org_context",
    "get_session",
    "list_agents",
    "list_policies",
    "list_sessions",
    "list_tool_definitions",
    "record_verdict",
    "search_tool_calls",
]

CLEAN = {
    "risky": False,
    "severity": "none",
    "categories": [],
    "policy_ids": [],
    "flagged_call_ids": [],
    "rationale": "Every call is within the agent's permissions.",
}


def test_mcp_arn_env_var(config: Config):
    """The variable bind() sets for AuditMcp, named in cdk-stack.ts."""
    name = config.agentcore_runtime_name_audit_mcp
    assert get_runtime_arn_env_var(name) == "AGENTCORE_RUNTIME_AUDITMCP_ARN"


def test_record_verdict_tool():
    """
    The tool the LLM sees: the function's description, its parameters without
    the injected log, every one described and required; calling it records.
    """
    log = VerdictLog()
    tool = make_record_verdict_tool(log)
    spec = tool.tool_spec
    assert spec["name"] == "record_verdict"
    assert spec["description"].startswith("Record your verdict on one session")
    schema = spec["inputSchema"]["json"]
    assert list(schema["properties"]) == list(definition.SessionVerdict.model_fields)
    assert schema["required"] == list(schema["properties"])
    for field in schema["properties"].values():
        assert field["description"]
    assert schema["properties"]["severity"]["enum"] == [
        "none",
        "low",
        "medium",
        "high",
        "critical",
    ]
    receipt = tool(session_id="ses_001", **CLEAN)
    assert receipt.num_recorded == 1
    assert [verdict.session_id for verdict in log.verdicts] == ["ses_001"]


def test_make_agent(mcp_url):
    """
    The agent has its own tool and the MCP tools, loaded over HTTP, and a model
    on the Anthropic API with the key it was given; no LLM call.
    """
    log = ModelLog()
    agent = make_agent(
        "acme-widget-model-1",
        "fake-key",
        mcp_url,
        VerdictLog(),
        fallback_model_id="acme-widget-model-0",
        model_log=log,
    )
    try:
        assert sorted(agent.tool_names) == TOOL_NAMES
        assert agent.system_prompt == definition.SYSTEM_PROMPT
        model_config = agent.model.get_config()
        assert model_config["model_id"] == "acme-widget-model-1"
        assert model_config["max_tokens"] == audit_agent.MAX_TOKENS
        assert model_config["cache_config"].strategy == "auto"
        assert agent.model.client.api_key == "fake-key"
        assert agent.model.fallback_model_id == "acme-widget-model-0"
        assert agent.model.model_log is log
        # every model call asks for the server-side fallback: the beta header
        # and the body field reach the Anthropic SDK as its extra_* arguments
        request = agent.model.format_request(
            messages=[{"role": "user", "content": [{"text": "hi"}]}],
        )
        assert request["extra_body"] == {"fallbacks": "default"}
        assert request["extra_headers"]["anthropic-beta"].startswith(
            "server-side-fallback-"
        )
    finally:
        agent.cleanup()


def test_build_agent(mcp_url, monkeypatch):
    """With the dependencies of the process: here the local MCP server of MCP_URL_AUDITMCP."""
    monkeypatch.setenv("MCP_URL_AUDITMCP", mcp_url)
    agent = build_agent()
    try:
        assert sorted(agent.tool_names) == TOOL_NAMES
        # the model and its key are the ones of the config
        model_id = agent.model.get_config()["model_id"]
        assert model_id == one.config.audit_agent_model_id
        assert agent.model.client.api_key == one.config.anthropic_api_key
        fallback_model_id = agent.model.fallback_model_id
        assert fallback_model_id == one.config.audit_agent_fallback_model_id
        # the agent's model writes to the log invoke() reads
        assert agent.model.model_log is model_log
        # the agent's tool writes to the log invoke() reads
        agent.tool.record_verdict(session_id="ses_002", **CLEAN)
        assert [verdict.session_id for verdict in verdict_log.verdicts] == ["ses_002"]
    finally:
        agent.cleanup()
        verdict_log.clear()


class FakeAgent:
    """
    Stands in for the Strands agent: records a verdict on the session the
    prompt names, as the model would through the tool, then answers. A prompt
    that starts with ``refused`` is one the model declines after that. Its
    model notes itself in the log first, as the real one does.
    """

    def __call__(self, prompt):
        model_log.record(f"model-for-{prompt}")
        definition.record_verdict(verdict_log, session_id=prompt, **CLEAN)
        if prompt.startswith("refused"):
            return FakeAgentResult("", stop_reason="refusal")
        return FakeAgentResult(f"<thinking>hmm</thinking> answer to {prompt}")

    def cleanup(self):
        pass


def test_invoke(monkeypatch):
    """
    The answer of the agent of the process, without the model's thinking, and
    the verdicts recorded for this answer only: none left over from the last.
    """
    monkeypatch.setattr(audit_agent, "agent", ProcessAgent(FakeAgent))
    answer = invoke({"prompt": "ses_001"})
    assert answer["result"] == "answer to ses_001"
    assert answer["verdicts"] == [{"session_id": "ses_001", **CLEAN}]
    assert answer["models"] == ["model-for-ses_001"]
    answer = invoke({"prompt": "ses_003"})
    assert [verdict["session_id"] for verdict in answer["verdicts"]] == ["ses_003"]
    assert answer["refused"] is False
    # the models of this answer only
    assert answer["models"] == ["model-for-ses_003"]


def test_invoke_refused(monkeypatch):
    """
    A request the model declines is answered, not failed and not left empty:
    the refusal in words and as data, without the verdict recorded before the
    model stopped. The agent is dropped, so the next request is a new
    conversation.
    """
    built = []

    def build():
        built.append(FakeAgent())
        return built[-1]

    monkeypatch.setattr(audit_agent, "agent", ProcessAgent(build))
    answer = invoke({"prompt": "refused ses_004"})
    assert answer == {
        "result": definition.REFUSAL_ANSWER,
        "verdicts": [],
        "refused": True,
        "models": ["model-for-refused ses_004"],
    }
    answer = invoke({"prompt": "ses_005"})
    assert answer["refused"] is False
    assert [verdict["session_id"] for verdict in answer["verdicts"]] == ["ses_005"]
    assert len(built) == 2


def test_invoke_bad_payload(monkeypatch):
    """A payload that does not validate is a 400 naming the field; no agent is built."""
    built = []
    monkeypatch.setattr(audit_agent, "agent", ProcessAgent(lambda: built.append(1)))
    with pytest.raises(HTTPException) as info:
        invoke({"question": "hi"})
    assert info.value.status_code == 400
    assert info.value.detail[0]["loc"] == ("prompt",)
    assert built == []


def test_main(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(app, "run", lambda: calls.append("run"))
    main()
    assert calls == ["run"]
    assert "Loaded the config of 'dev'" in capsys.readouterr().out


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.runtimes.audit_agent",
        preview=False,
    )
