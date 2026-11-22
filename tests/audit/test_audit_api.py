# -*- coding: utf-8 -*-

from agent_app.audit import api


def test():
    _ = api
    _ = api.Policy
    _ = api.VerifiedVendor
    _ = api.OrgContext
    _ = api.ToolDefinition
    _ = api.AgentInfo
    _ = api.AgentDetail
    _ = api.AgentSnapshot
    _ = api.Trigger
    _ = api.Approval
    _ = api.ToolCall
    _ = api.SessionInfo
    _ = api.SessionDetail
    _ = api.SessionPage
    _ = api.ToolCallMatch
    _ = api.ToolCallPage
    _ = api.AuditStore
    _ = api.load_audit_store
    _ = api.list_policies
    _ = api.get_org_context
    _ = api.list_tool_definitions
    _ = api.list_agents
    _ = api.get_agent
    _ = api.list_sessions
    _ = api.get_session
    _ = api.search_tool_calls
    _ = api.SYSTEM_PROMPT
    _ = api.Severity
    _ = api.AuditAgentRequest
    _ = api.AuditAgentResponse
    _ = api.REFUSAL_ANSWER
    _ = api.refused_response
    _ = api.SessionVerdict
    _ = api.VerdictReceipt
    _ = api.VerdictLog
    _ = api.record_verdict


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.audit.api",
        preview=False,
    )
