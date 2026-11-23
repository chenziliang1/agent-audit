# -*- coding: utf-8 -*-

"""
Read-only queries over the audit data, exposed as MCP tools by
:mod:`~agent_app.runtimes.audit_mcp`.

They hand over evidence and nothing else: who the agent was, what it was
allowed to do, what it was asked, what it called, and what the company's rules
say. Whether a call is a violation is for the caller to decide.

Every function takes the store first and returns the models of
:mod:`~agent_app.audit.schemas`. The first paragraph of each docstring is the
tool description the LLM reads, so it does not mention the store.
"""

from __future__ import annotations

import json

from .store import AuditStore
from .schemas import Policy
from .schemas import OrgContext
from .schemas import ToolDefinition
from .schemas import AgentInfo
from .schemas import AgentList
from .schemas import AgentDetail
from .schemas import SessionInfo
from .schemas import SessionDetail
from .schemas import SessionPage
from .schemas import ToolCall
from .schemas import ToolCallMatch
from .schemas import ToolCallPage

#: The largest page a list or search tool returns.
MAX_LIMIT = 100


def check_page(limit: int, offset: int) -> None:
    """
    :raises ValueError: if ``limit`` or ``offset`` is out of range.
    """
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}, got {limit}")
    if offset < 0:
        raise ValueError(f"offset must be 0 or more, got {offset}")


def check_agent(store: AuditStore, agent_id: str) -> None:
    """
    Raise if ``agent_id`` is not the ID of an audited agent.

    A filter on an agent that does not exist would otherwise answer with an
    empty page, which reads as "this agent did nothing". People name an agent
    by its name, so the usual wrong value is a name: the message then gives the
    ID that name has, and the caller can correct itself in one step.

    :raises ValueError: if the agent does not exist.
    """
    if agent_id in store.agents:
        return
    for agent in store.agents.values():
        if agent.name.casefold() == agent_id.casefold():
            raise ValueError(
                f"agent {agent_id!r} not found: that is the name of the agent "
                f"whose agent_id is {agent.agent_id!r}"
            )
    raise ValueError(
        f"agent {agent_id!r} not found: list_agents gives the agent_id of every agent"
    )


def to_session_info(session: SessionDetail) -> SessionInfo:
    """
    The brief form of a session.
    """
    return SessionInfo(
        session_id=session.session_id,
        agent_id=session.agent_id,
        agent_name=session.agent.name,
        agent_role=session.agent.role,
        task=session.task,
        trigger=session.trigger,
        environment=session.environment,
        started_at=session.started_at,
        ended_at=session.ended_at,
        status=session.status,
        num_tool_calls=session.num_tool_calls,
    )


def list_policies(store: AuditStore) -> list[Policy]:
    """
    List every rule of the company's tool-use security policy. Read these
    before judging any tool call: a finding must cite the rule it breaks.
    """
    return list(store.policies)


def get_org_context(store: AuditStore) -> OrgContext:
    """
    Get the company facts the policy rules refer to: which domains are internal
    or approved partners, which external hosts are allow-listed, the refund and
    payout approval limits, the runaway-loop threshold, and the vendors with a
    verified bank account.
    """
    return store.org


def list_tool_definitions(
    store: AuditStore,
    side_effect: str | None = None,
) -> list[ToolDefinition]:
    """
    List the tools the audited agents can be given, with what each does and its
    parameters, optionally only those of one ``side_effect`` (``read``,
    ``write``, ``read/write``, ``external``, ``financial``, ``sensitive``, or
    ``privileged``).
    """
    tools = store.tools
    if side_effect is not None:
        tools = [tool for tool in tools if tool.side_effect == side_effect]
    return list(tools)


def list_agents(
    store: AuditStore,
    role: str | None = None,
) -> AgentList:
    """
    List the audited agents, optionally only those of one ``role`` (such as
    ``support``, ``devops``, ``coding``, ``analyst``, ``finance``), with how
    many there are.
    """
    agents = store.agents.values()
    if role is not None:
        agents = [agent for agent in agents if agent.role == role]
    infos = [
        AgentInfo(
            agent_id=agent.agent_id,
            name=agent.name,
            role=agent.role,
            team=agent.team,
            environment=agent.environment,
        )
        for agent in agents
    ]
    # The count is stated because an LLM that counts a long list itself gets it
    # wrong now and then: it once reported 25 agents as 26.
    return AgentList(total=len(infos), agents=infos)


def get_agent(
    store: AuditStore,
    agent_id: str,
) -> AgentDetail:
    """
    Get one audited agent with everything it is permitted to do: its
    ``allowed_tools``, its ``limits``, its owner, and its service account.
    ``agent_id`` is the ID list_agents gives, such as ``agt_...``, not the
    agent's name.

    :raises ValueError: if the agent does not exist.
    """
    check_agent(store, agent_id)
    return store.agents[agent_id]


def list_sessions(
    store: AuditStore,
    agent_id: str | None = None,
    status: str | None = None,
    tool: str | None = None,
    started_from: str | None = None,
    started_before: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> SessionPage:
    """
    List recorded sessions, oldest first, one page at a time. Filters, all
    optional: ``agent_id``, the ID list_agents gives, not the agent's name;
    ``status`` (``completed``, ``failed``, or ``aborted``); ``tool``, sessions
    that called this tool at least once; ``started_from`` (inclusive) and
    ``started_before`` (exclusive), ISO 8601 UTC such as ``2026-11-06`` or
    ``2026-11-06T12:00:00Z``. ``total`` counts every match; page with ``limit``
    (at most 100) and ``offset``.

    :raises ValueError: if ``limit`` or ``offset`` is out of range, or the
        agent does not exist.
    """
    check_page(limit, offset)
    if agent_id is not None:
        check_agent(store, agent_id)
    matches = []
    for session in store.sessions.values():
        if agent_id is not None and session.agent_id != agent_id:
            continue
        if status is not None and session.status != status:
            continue
        if started_from is not None and session.started_at < started_from:
            continue
        if started_before is not None and session.started_at >= started_before:
            continue
        if tool is not None and all(call.tool != tool for call in session.tool_calls):
            continue
        matches.append(session)
    page = matches[offset : offset + limit]
    return SessionPage(
        total=len(matches),
        offset=offset,
        sessions=[to_session_info(session) for session in page],
    )


def get_session(
    store: AuditStore,
    session_id: str,
) -> SessionDetail:
    """
    Get one session in full: the task the agent was given, what triggered it,
    the agent's permissions at the time, and every tool call in order with its
    arguments, status, approval, and result. This is the evidence an audit of
    the session rests on.

    :raises ValueError: if the session does not exist.
    """
    session = store.sessions.get(session_id)
    if session is None:
        raise ValueError(f"session {session_id!r} not found")
    return session


def call_matches_text(call: ToolCall, text: str) -> bool:
    """
    Whether ``text``, lower case, occurs in the arguments or the result of ``call``.
    """
    haystack = json.dumps([call.arguments, call.result], ensure_ascii=False)
    return text in haystack.lower()


def search_tool_calls(
    store: AuditStore,
    tool: str | None = None,
    agent_id: str | None = None,
    status: str | None = None,
    text: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> ToolCallPage:
    """
    Search tool calls across all sessions, oldest session first. Filters, all
    optional: ``tool``, the exact tool name; ``agent_id``, the ID list_agents
    gives, not the agent's name; ``status`` (``success``, ``error``, or
    ``denied``); ``text``, a case-insensitive substring of the call's arguments
    or result, such as ``0.0.0.0/0``. Each match names its session: read that
    session before judging the call. ``total`` counts every match; page with
    ``limit`` (at most 100) and ``offset``.

    :raises ValueError: if ``limit`` or ``offset`` is out of range, or the
        agent does not exist.
    """
    check_page(limit, offset)
    if agent_id is not None:
        check_agent(store, agent_id)
    if text is not None:
        text = text.lower()
    matches = []
    for session in store.sessions.values():
        if agent_id is not None and session.agent_id != agent_id:
            continue
        for call in session.tool_calls:
            if tool is not None and call.tool != tool:
                continue
            if status is not None and call.status != status:
                continue
            if text is not None and not call_matches_text(call, text):
                continue
            matches.append((session, call))
    page = matches[offset : offset + limit]
    return ToolCallPage(
        total=len(matches),
        offset=offset,
        calls=[
            ToolCallMatch(
                session_id=session.session_id,
                agent_id=session.agent_id,
                agent_name=session.agent.name,
                task=session.task,
                call=call,
            )
            for session, call in page
        ],
    )
