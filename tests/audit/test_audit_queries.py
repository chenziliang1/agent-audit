# -*- coding: utf-8 -*-

from agent_app.audit.queries import MAX_LIMIT
from agent_app.audit.queries import list_policies
from agent_app.audit.queries import get_org_context
from agent_app.audit.queries import list_tool_definitions
from agent_app.audit.queries import list_agents
from agent_app.audit.queries import get_agent
from agent_app.audit.queries import list_sessions
from agent_app.audit.queries import get_session
from agent_app.audit.queries import search_tool_calls

import pytest

from agent_app.audit.schemas import AgentInfo
from agent_app.audit.schemas import SessionInfo
from agent_app.audit.schemas import Trigger


def test_list_policies(audit_store):
    policies = list_policies(audit_store)
    assert [policy.policy_id for policy in policies] == ["P-01", "P-02"]
    assert policies is not audit_store.policies


def test_get_org_context(audit_store):
    org = get_org_context(audit_store)
    assert org.refund_limit_usd == 200
    assert org.partner_domains == ["partner.test"]


def test_list_tool_definitions(audit_store):
    assert len(list_tool_definitions(audit_store)) == 3
    tools = list_tool_definitions(audit_store, side_effect="financial")
    assert [tool.name for tool in tools] == ["payments.refund"]
    assert list_tool_definitions(audit_store, side_effect="magic") == []


def test_list_agents(audit_store):
    agents = list_agents(audit_store)
    assert agents[0] == AgentInfo(
        agent_id="agt_a1",
        name="widget-helper-01",
        role="support",
        team="Widget Care",
        environment="production",
    )
    assert [agent.agent_id for agent in agents] == ["agt_a1", "agt_b2"]
    coders = list_agents(audit_store, role="coding")
    assert [agent.agent_id for agent in coders] == ["agt_b2"]
    assert list_agents(audit_store, role="pilot") == []


def test_get_agent(audit_store):
    agent = get_agent(audit_store, "agt_a1")
    assert agent.allowed_tools == ["ticket.get", "email.send", "payments.refund"]
    assert agent.limits == {"max_steps_per_session": 80, "refund_limit_usd": 200}
    with pytest.raises(ValueError, match="agent 'agt_zz' not found"):
        get_agent(audit_store, "agt_zz")


@pytest.mark.parametrize(
    "agent_id, message",
    [
        # An ID nobody has: the message says where the IDs are.
        (
            "agt_zz",
            "agent 'agt_zz' not found: list_agents gives the agent_id of every agent",
        ),
        # An agent's name, in any case: the message gives the ID it stands for.
        (
            "widget-helper-01",
            "that is the name of the agent whose agent_id is 'agt_a1'",
        ),
        (
            "Widget-Helper-01",
            "that is the name of the agent whose agent_id is 'agt_a1'",
        ),
    ],
)
def test_unknown_agent(audit_store, agent_id, message):
    # A filter on an agent that does not exist is an error, never an empty page.
    with pytest.raises(ValueError, match=message):
        get_agent(audit_store, agent_id)
    with pytest.raises(ValueError, match=message):
        list_sessions(audit_store, agent_id=agent_id)
    with pytest.raises(ValueError, match=message):
        search_tool_calls(audit_store, agent_id=agent_id)


def test_list_sessions(audit_store):
    page = list_sessions(audit_store)
    assert page.total == 3
    assert page.offset == 0
    assert page.sessions[0] == SessionInfo(
        session_id="ses_001",
        agent_id="agt_a1",
        agent_name="widget-helper-01",
        agent_role="support",
        task="Resolve ticket TCK-1",
        trigger=Trigger(type="user", source="slack:#widgets"),
        environment="production",
        started_at="2026-01-05T09:00:00Z",
        ended_at="2026-01-05T09:00:30.000Z",
        status="completed",
        num_tool_calls=2,
    )


@pytest.mark.parametrize(
    "filters, expected_ids",
    [
        ({"agent_id": "agt_a1"}, ["ses_001", "ses_002"]),
        ({"status": "failed"}, ["ses_002"]),
        ({"tool": "git.push"}, ["ses_003"]),
        ({"tool": "db.query"}, []),
        ({"started_from": "2026-01-06"}, ["ses_002", "ses_003"]),
        ({"started_before": "2026-01-06"}, ["ses_001"]),
        (
            {"started_from": "2026-01-06T10:00:00Z", "started_before": "2026-01-07"},
            ["ses_002"],
        ),
        ({"agent_id": "agt_a1", "status": "completed"}, ["ses_001"]),
    ],
)
def test_list_sessions_filters(audit_store, filters, expected_ids):
    page = list_sessions(audit_store, **filters)
    assert [session.session_id for session in page.sessions] == expected_ids
    assert page.total == len(expected_ids)


def test_list_sessions_pages(audit_store):
    page = list_sessions(audit_store, limit=2, offset=1)
    assert page.total == 3
    assert page.offset == 1
    assert [session.session_id for session in page.sessions] == ["ses_002", "ses_003"]
    assert list_sessions(audit_store, offset=5).sessions == []


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"limit": 0}, "limit must be between 1 and 100, got 0"),
        ({"limit": MAX_LIMIT + 1}, "limit must be between 1 and 100, got 101"),
        ({"offset": -1}, "offset must be 0 or more, got -1"),
    ],
)
def test_page_out_of_range(audit_store, kwargs, message):
    with pytest.raises(ValueError, match=message):
        list_sessions(audit_store, **kwargs)
    with pytest.raises(ValueError, match=message):
        search_tool_calls(audit_store, **kwargs)


def test_get_session(audit_store):
    session = get_session(audit_store, "ses_001")
    assert session.task == "Resolve ticket TCK-1"
    assert session.agent.allowed_tools == [
        "ticket.get",
        "email.send",
        "payments.refund",
    ]
    assert [call.tool for call in session.tool_calls] == [
        "ticket.get",
        "payments.refund",
    ]
    assert session.tool_calls[1].arguments == {"order_id": "ORD-1", "amount": 350}
    assert session.tool_calls[1].approval.approved_by == "road.runner@acme.test"
    with pytest.raises(ValueError, match="session 'ses_999' not found"):
        get_session(audit_store, "ses_999")


def test_search_tool_calls(audit_store):
    page = search_tool_calls(audit_store)
    assert page.total == 5
    assert [match.call.call_id for match in page.calls] == [
        "call_1",
        "call_2",
        "call_3",
        "call_4",
        "call_5",
    ]
    match = page.calls[3]
    assert match.session_id == "ses_003"
    assert match.agent_id == "agt_b2"
    assert match.agent_name == "part-builder-01"
    assert match.task == "Set up the part builder"


@pytest.mark.parametrize(
    "filters, expected_ids",
    [
        ({"tool": "payments.refund"}, ["call_2"]),
        ({"agent_id": "agt_a1"}, ["call_1", "call_2", "call_3"]),
        ({"status": "denied"}, ["call_4"]),
        ({"status": "error"}, ["call_3"]),
        # in the arguments, whatever the case
        ({"text": "PARTS.example.test"}, ["call_4"]),
        # in the result
        ({"text": "smtp 503"}, ["call_3"]),
        ({"text": "ord-1"}, ["call_1", "call_2"]),
        ({"text": "ord-1", "tool": "ticket.get"}, ["call_1"]),
        ({"text": "no such text"}, []),
    ],
)
def test_search_tool_calls_filters(audit_store, filters, expected_ids):
    page = search_tool_calls(audit_store, **filters)
    assert [match.call.call_id for match in page.calls] == expected_ids
    assert page.total == len(expected_ids)


def test_search_tool_calls_pages(audit_store):
    page = search_tool_calls(audit_store, limit=2, offset=3)
    assert page.total == 5
    assert page.offset == 3
    assert [match.call.call_id for match in page.calls] == ["call_4", "call_5"]


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.audit.queries",
        preview=False,
    )
