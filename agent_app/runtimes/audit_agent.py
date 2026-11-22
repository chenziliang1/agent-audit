# -*- coding: utf-8 -*-

"""
The ``AuditAgent`` runtime: the agent of :mod:`~agent_app.audit.audit_agent` as
a Strands agent, with the ``AuditMcp`` tools, served by
:class:`BedrockAgentCoreApp` (``POST /invocations`` and ``GET /ping`` on port
8080, the AgentCore HTTP contract; the same server runs locally).

A thin layer: :func:`make_agent` assembles the agent from what it is given;
:func:`build_agent` gives it the dependencies of this process (the model ID and
the API key of the config, the MCP connection, the verdict log);
:data:`agent` keeps one agent per process (see
:class:`~agent_app.runtimes.common.ProcessAgent`).
"""

from __future__ import annotations

import threading

import httpx
import pydantic
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from starlette.exceptions import HTTPException
from strands import Agent
from strands import tool
from strands.models import CacheConfig
from strands.tools.mcp import MCPClient

from ..one.api import one
from ..audit import audit_agent
from ..audit.audit_agent import SYSTEM_PROMPT
from ..audit.audit_agent import Severity
from ..audit.audit_agent import VerdictLog
from ..audit.audit_agent import VerdictReceipt
from ..audit.audit_agent import AuditAgentRequest
from ..audit.audit_agent import AuditAgentResponse
from ..audit.audit_agent import refused_response
from .common import ProcessAgent
from .common import ModelRefusal
from .common import doc_from
from .common import strip_thinking
from .common import print_config_source
from .fallback_model import FallbackAnthropicModel
from .mcp_connection import get_mcp_connection

#: The most the model may write in one model call, its thinking included. The
#: answers are short; the room is for the thinking and for a tool call that
#: names many tool calls.
MAX_TOKENS = 32000

#: Sent with every model call: when the model's safety classifiers decline a
#: call, the Anthropic API runs it again on the fallback model it recommends for
#: that kind of refusal, inside the same call. An audited session quotes attacks
#: (injected instructions, exfiltration commands), so without this the model
#: refuses exactly the sessions that matter. The API does not always fall back
#: (:mod:`~agent_app.runtimes.fallback_model` covers that), not every kind of
#: refusal has a fallback, and the fallback model can refuse too: see
#: :class:`~agent_app.runtimes.common.ModelRefusal`.
#:
#: Strands passes these to the Anthropic SDK's ``messages.stream``, which has
#: no argument for either: a beta feature, hence a header and a body field.
FALLBACK_PARAMS = {
    "extra_headers": {"anthropic-beta": "server-side-fallback-2026-07-01"},
    "extra_body": {"fallbacks": "default"},
}


def make_record_verdict_tool(log: VerdictLog):
    """
    The agent's own tool: :func:`~agent_app.audit.audit_agent.record_verdict`
    with its dependency, the verdict log, injected here, so the LLM never sees
    it. The tool's description and parameter descriptions are the function's
    docstring.
    """

    @tool
    @doc_from(audit_agent.record_verdict)
    def record_verdict(
        session_id: str,
        risky: bool,
        severity: Severity,
        categories: list[str],
        policy_ids: list[str],
        flagged_call_ids: list[str],
        rationale: str,
    ) -> VerdictReceipt:
        return audit_agent.record_verdict(
            log,
            session_id=session_id,
            risky=risky,
            severity=severity,
            categories=categories,
            policy_ids=policy_ids,
            flagged_call_ids=flagged_call_ids,
            rationale=rationale,
        )

    return record_verdict


def make_agent(
    model_id: str,
    api_key: str,
    mcp_url: str,
    log: VerdictLog,
    mcp_auth: httpx.Auth | None = None,
    fallback_model_id: str | None = None,
) -> Agent:
    """
    The agent on the Claude model ``model_id``, called on the Anthropic API
    with ``api_key``, with its own tool writing to ``log`` and the tools of the
    MCP server at ``mcp_url``. ``agent.cleanup()`` closes the MCP connection.

    The model is called directly, not through Amazon Bedrock, so nothing here
    needs AWS; only a deployed MCP connection does (``mcp_auth``).

    Prompt caching is on: the system prompt and the tool definitions are the
    same on every model call of a conversation, and one audit makes several.

    A call ``model_id`` declines may be answered by another Claude model: the
    one the Anthropic API falls back to (:data:`FALLBACK_PARAMS`), or
    ``fallback_model_id`` when the API returns the refusal instead
    (:class:`~agent_app.runtimes.fallback_model.FallbackAnthropicModel`). So
    ``model_id`` is the model asked first, not always the one that judged.
    """
    return Agent(
        model=FallbackAnthropicModel(
            fallback_model_id=fallback_model_id,
            client_args={"api_key": api_key},
            model_id=model_id,
            max_tokens=MAX_TOKENS,
            cache_config=CacheConfig(strategy="auto", tools_ttl=True),
            params=FALLBACK_PARAMS,
        ),
        system_prompt=SYSTEM_PROMPT,
        tools=[
            make_record_verdict_tool(log),
            MCPClient(url=mcp_url, auth_provider=mcp_auth),
        ],
        callback_handler=None,
    )


#: The verdicts of the invocation in progress; the agent's tool writes to it.
verdict_log = VerdictLog()


def build_agent() -> Agent:
    """
    :func:`make_agent` with the dependencies of this process: ``audit_agent_model_id``,
    ``audit_agent_fallback_model_id`` and ``anthropic_api_key`` of the config, the ``AuditMcp`` connection, and
    :data:`verdict_log`.

    The boto session only signs the requests to a deployed MCP runtime; a local
    MCP server is reached without it. It is a new session of the environment
    (the local profile, or the runtime's execution role), made now, on the
    first invocation, never at import time.
    """
    mcp_url, mcp_auth = get_mcp_connection(
        runtime_name=one.config.agentcore_runtime_name_audit_mcp,
        boto_session=one.new_boto_ses(),
    )
    return make_agent(
        model_id=one.config.audit_agent_model_id,
        api_key=one.config.anthropic_api_key,
        mcp_url=mcp_url,
        log=verdict_log,
        mcp_auth=mcp_auth,
        fallback_model_id=one.config.audit_agent_fallback_model_id,
    )


#: The agent of this process, built by :func:`build_agent` on the first invocation.
agent = ProcessAgent(build_agent)

#: One invocation at a time, from emptying the verdict log to reading it: the
#: verdicts returned are the ones of this invocation, never of a concurrent one.
_invoke_lock = threading.Lock()

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    """
    Answer an :class:`AuditAgentRequest` with an :class:`AuditAgentResponse`,
    as JSON: the agent's text, and the verdicts it recorded while answering. A
    payload that does not validate is the caller's mistake: a 400 with
    pydantic's errors, before the agent is built or the model called
    (``BedrockAgentCoreApp`` answers any other exception with a 500).

    A request the model declines is answered too, with a 200: the request was
    valid, and the caller must be able to tell "refused" from "audited, nothing
    found" (:func:`~agent_app.audit.audit_agent.refused_response`).
    """
    try:
        request = AuditAgentRequest.model_validate(payload)
    except pydantic.ValidationError as e:
        errors = e.errors(include_url=False, include_context=False, include_input=False)
        raise HTTPException(status_code=400, detail=errors)
    with _invoke_lock:
        verdict_log.clear()
        try:
            answer = strip_thinking(agent(request.prompt))
        except ModelRefusal:
            app.logger.warning("The model declined to answer; conversation reset")
            return refused_response().model_dump()
        verdicts = verdict_log.verdicts
    return AuditAgentResponse(result=answer, verdicts=verdicts).model_dump()


def main():
    """
    Load the config, then serve on port 8080, blocking until stopped.
    ``agentcore dev`` serves ``app`` with uvicorn instead, so there the config
    is loaded on the first request.
    """
    print_config_source()
    app.run()


if __name__ == "__main__":
    main()
