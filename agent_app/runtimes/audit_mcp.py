# -*- coding: utf-8 -*-

"""
The ``AuditMcp`` runtime: an MCP server exposing the read-only audit queries of
:mod:`~agent_app.audit.queries`.

A thin layer: each tool calls its query with the dependency it needs, the audit
data of the process (``one.audit_store``), injected here, so the LLM never sees
it. The description of a tool is its query's docstring, and its output schema
comes from the query's Pydantic return type.
"""

from __future__ import annotations

from ..one.api import one
from ..audit import queries
from ..audit.schemas import Policy
from ..audit.schemas import OrgContext
from ..audit.schemas import ToolDefinition
from ..audit.schemas import AgentList
from ..audit.schemas import AgentDetail
from ..audit.schemas import SessionPage
from ..audit.schemas import SessionDetail
from ..audit.schemas import ToolCallPage
from .common import new_mcp_server
from .common import run_mcp_server
from .common import doc_from
from .common import print_config_source

#: The MCP server, named after the runtime in ``agentcore.json``.
mcp = new_mcp_server("AuditMcp")


@mcp.tool()
@doc_from(queries.list_policies)
def list_policies() -> list[Policy]:
    return queries.list_policies(one.audit_store)


@mcp.tool()
@doc_from(queries.get_org_context)
def get_org_context() -> OrgContext:
    return queries.get_org_context(one.audit_store)


@mcp.tool()
@doc_from(queries.list_tool_definitions)
def list_tool_definitions(side_effect: str | None = None) -> list[ToolDefinition]:
    return queries.list_tool_definitions(one.audit_store, side_effect=side_effect)


@mcp.tool()
@doc_from(queries.list_agents)
def list_agents(role: str | None = None) -> AgentList:
    return queries.list_agents(one.audit_store, role=role)


@mcp.tool()
@doc_from(queries.get_agent)
def get_agent(agent_id: str) -> AgentDetail:
    return queries.get_agent(one.audit_store, agent_id=agent_id)


@mcp.tool()
@doc_from(queries.list_sessions)
def list_sessions(
    agent_id: str | None = None,
    status: str | None = None,
    tool: str | None = None,
    started_from: str | None = None,
    started_before: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> SessionPage:
    return queries.list_sessions(
        one.audit_store,
        agent_id=agent_id,
        status=status,
        tool=tool,
        started_from=started_from,
        started_before=started_before,
        limit=limit,
        offset=offset,
    )


@mcp.tool()
@doc_from(queries.get_session)
def get_session(session_id: str) -> SessionDetail:
    return queries.get_session(one.audit_store, session_id=session_id)


@mcp.tool()
@doc_from(queries.search_tool_calls)
def search_tool_calls(
    tool: str | None = None,
    agent_id: str | None = None,
    status: str | None = None,
    text: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> ToolCallPage:
    return queries.search_tool_calls(
        one.audit_store,
        tool=tool,
        agent_id=agent_id,
        status=status,
        text=text,
        limit=limit,
        offset=offset,
    )


def main():
    """
    Load the config and the audit data, then serve, blocking until stopped. A
    runtime that cannot read its config or whose data does not validate fails
    here, at startup.
    """
    print_config_source()
    store = one.audit_store
    print(
        f"Loaded the audit data: {len(store.agents)} agents, "
        f"{len(store.sessions)} sessions, {store.num_tool_calls} tool calls",
        flush=True,
    )
    run_mcp_server(mcp)


if __name__ == "__main__":
    main()
