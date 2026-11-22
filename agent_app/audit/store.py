# -*- coding: utf-8 -*-

"""
The audit data in memory: the policy, the company facts, the tool catalog, the
audited agents, and every recorded session, loaded once from the files bundled
in ``audit/data/``.

There is no database. The whole dataset is a few megabytes, it is read only,
and every question the tools answer is a filter over one list, so an index by
ID is all the structure it needs.

The files are a copy of the dataset's *inputs* only. Its ground-truth labels
are never bundled, and :mod:`~agent_app.audit.schemas` rejects any record that
carries a field it does not know, so a mislabelled copy fails to load rather
than leaking an answer.
"""

from __future__ import annotations

import gzip
import json
import dataclasses
from pathlib import Path

from .schemas import Policy
from .schemas import OrgContext
from .schemas import ToolDefinition
from .schemas import AgentDetail
from .schemas import SessionDetail

#: The company's policy rules, a JSON list.
POLICY_FILE = "policy.json"
#: The company facts the rules refer to, a JSON object.
ORG_FILE = "org.json"
#: The catalog of tools agents can be given, a JSON list.
TOOLS_FILE = "tools.json"
#: The audited agents, one JSON object per line.
AGENTS_FILE = "agents.jsonl"
#: Every session with its tool calls, one JSON object per line, gzipped.
TRACES_FILE = "traces.jsonl.gz"


@dataclasses.dataclass
class AuditStore:
    """
    Everything the audit tools read. Build it with :func:`load_audit_store`.
    """

    # fmt: off
    policies: list[Policy] = dataclasses.field()  #: In the order of the policy document.
    org: OrgContext = dataclasses.field()  #: The company facts.
    tools: list[ToolDefinition] = dataclasses.field()  #: In the order of the catalog.
    agents: dict[str, AgentDetail] = dataclasses.field()  #: By agent ID, in file order.
    sessions: dict[str, SessionDetail] = dataclasses.field()  #: By session ID, oldest first.
    # fmt: on

    @property
    def num_tool_calls(self) -> int:
        """
        How many tool calls all sessions have together.
        """
        return sum(len(session.tool_calls) for session in self.sessions.values())


def read_json_lines(text: str) -> list[dict]:
    """
    Parse one JSON object per non-empty line.
    """
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def load_audit_store(dir_data: Path) -> AuditStore:
    """
    Load and validate the audit data in ``dir_data``.

    :raises pydantic.ValidationError: a record has a missing or an unknown
        field, such as a ground-truth label.
    :raises ValueError: a session belongs to an agent that is not in the
        agents file.
    """
    policies = json.loads((dir_data / POLICY_FILE).read_text(encoding="utf-8"))
    org = json.loads((dir_data / ORG_FILE).read_text(encoding="utf-8"))
    tools = json.loads((dir_data / TOOLS_FILE).read_text(encoding="utf-8"))
    agents = read_json_lines((dir_data / AGENTS_FILE).read_text(encoding="utf-8"))
    with gzip.open(dir_data / TRACES_FILE, "rt", encoding="utf-8") as f:
        sessions = read_json_lines(f.read())
    store = AuditStore(
        policies=[Policy.model_validate(row) for row in policies],
        org=OrgContext.model_validate(org),
        tools=[ToolDefinition.model_validate(row) for row in tools],
        agents={row["agent_id"]: AgentDetail.model_validate(row) for row in agents},
        sessions={},
    )
    rows = [SessionDetail.model_validate(row) for row in sessions]
    for session in sorted(rows, key=lambda row: (row.started_at, row.session_id)):
        if session.agent_id not in store.agents:
            raise ValueError(
                f"session {session.session_id!r} belongs to agent "
                f"{session.agent_id!r}, which is not in {AGENTS_FILE}"
            )
        store.sessions[session.session_id] = session
    return store
