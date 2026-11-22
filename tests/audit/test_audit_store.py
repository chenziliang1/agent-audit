# -*- coding: utf-8 -*-

from agent_app.audit.store import AuditStore
from agent_app.audit.store import read_json_lines
from agent_app.audit.store import load_audit_store

import gzip
import json
import shutil

import pytest
from pydantic import ValidationError


def test_read_json_lines():
    assert read_json_lines('{"a": 1}\n\n{"a": 2}\n') == [{"a": 1}, {"a": 2}]
    assert read_json_lines("") == []


def test_load_audit_store(audit_store: AuditStore):
    assert [policy.policy_id for policy in audit_store.policies] == ["P-01", "P-02"]
    assert audit_store.org.company == "Acme Corp"
    assert audit_store.org.verified_vendors[0].iban == "XX00PART0001"
    assert [tool.name for tool in audit_store.tools] == [
        "ticket.get",
        "payments.refund",
        "shell.exec",
    ]
    assert list(audit_store.agents) == ["agt_a1", "agt_b2"]
    # the file is not in time order; the store is
    assert list(audit_store.sessions) == ["ses_001", "ses_002", "ses_003"]
    assert audit_store.num_tool_calls == 5


def rewrite_sessions(dir_data, dir_copy, change):
    """
    Copy the bundled sample to ``dir_copy`` with ``change`` applied to its
    first session.
    """
    shutil.copytree(dir_data, dir_copy)
    with gzip.open(dir_copy / "traces.jsonl.gz", "rt") as f:
        sessions = [json.loads(line) for line in f]
    change(sessions[0])
    content = "\n".join(json.dumps(session) for session in sessions)
    (dir_copy / "traces.jsonl.gz").write_bytes(gzip.compress(content.encode()))


def test_load_rejects_a_label(dir_audit_data, tmp_path):
    """A session carrying a ground-truth field fails the whole load."""
    dir_copy = tmp_path / "labelled"
    rewrite_sessions(
        dir_audit_data,
        dir_copy,
        lambda session: session.update({"scenario": "widget_theft"}),
    )
    with pytest.raises(ValidationError, match="scenario"):
        load_audit_store(dir_copy)


def test_load_rejects_an_unknown_agent(dir_audit_data, tmp_path):
    dir_copy = tmp_path / "orphan"
    rewrite_sessions(
        dir_audit_data,
        dir_copy,
        lambda session: session.update({"agent_id": "agt_zz"}),
    )
    with pytest.raises(ValueError, match="agent 'agt_zz', which is not in"):
        load_audit_store(dir_copy)


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.audit.store",
        preview=False,
    )
