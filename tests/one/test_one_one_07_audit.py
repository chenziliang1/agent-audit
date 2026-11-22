# -*- coding: utf-8 -*-

from agent_app.one.one_07_audit import OneAuditMixin

from agent_app.paths import path_enum
from agent_app.one.api import One
from agent_app.audit.store import POLICY_FILE
from agent_app.audit.store import ORG_FILE
from agent_app.audit.store import TOOLS_FILE
from agent_app.audit.store import AGENTS_FILE
from agent_app.audit.store import TRACES_FILE


def test_audit_store():
    """
    The data bundled with the package loads, which also proves it validates:
    no record carries a field the models do not declare. Built once.
    """
    one = One()
    assert isinstance(one, OneAuditMixin)
    store = one.audit_store
    assert store.policies
    assert store.tools
    assert store.agents
    assert store.sessions
    assert store.num_tool_calls >= len(store.sessions)
    assert one.audit_store is store


def test_only_the_inputs_are_bundled():
    """
    The package directory holds the five input files and nothing else: no
    ``labels/``, no flat copy of the traces, no stats.
    """
    names = sorted(path.name for path in path_enum.dir_audit_data.iterdir())
    expected = [POLICY_FILE, ORG_FILE, TOOLS_FILE, AGENTS_FILE, TRACES_FILE]
    assert names == sorted(expected)


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.one.one_07_audit",
        preview=False,
    )
