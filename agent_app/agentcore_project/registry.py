# -*- coding: utf-8 -*-

"""
The runtime registry: every AgentCore Runtime of the project, in one list.

This is the one place a runtime is declared. Everything per runtime is derived
from it: ``agentcore/agentcore.json``, its code directory ``agentcore_app/<Runtime>/``,
and, through ``mise run gen-env-tasks``, its local, dev, call, invoke, and logs
tasks, with its local port and sample payload.
"""

from __future__ import annotations

import re
import enum
import dataclasses

from ..config.api import Config

#: The Python of every runtime; the dev Python, ``[tools] python`` in ``mise.toml``.
RUNTIME_PYTHON = "3.12"

#: :data:`RUNTIME_PYTHON` as AgentCore names it in ``agentcore.json``.
RUNTIME_VERSION = "PYTHON_" + RUNTIME_PYTHON.replace(".", "_")


class RuntimeProtocolEnum(enum.StrEnum):
    """
    The protocol AgentCore Runtime speaks with a runtime.
    """

    #: An MCP server: streamable HTTP on port 8000, path ``/mcp``.
    MCP = "MCP"
    #: An agent: ``POST /invocations`` and ``GET /ping`` on port 8080.
    HTTP = "HTTP"


@dataclasses.dataclass
class RuntimeSpec:
    """
    One AgentCore Runtime of the project.
    """

    # fmt: off
    name: str = dataclasses.field()  #: Name in ``agentcore.json``, from ``agentcore_runtime_name_*`` of the config.
    module: str = dataclasses.field()  #: The runtime module, relative to the package, such as ``runtimes.my_mcp``: it has a ``main()``, and an ``app`` for ``HTTP``.
    protocol: RuntimeProtocolEnum = dataclasses.field()  #: How AgentCore talks to it.
    sample_payload: dict = dataclasses.field()  #: What the call tasks send: ``{"prompt": ...}`` for an agent, a whole JSON-RPC ``tools/call`` request for an MCP server.
    local_port: int = dataclasses.field()  #: Its port on a developer machine, unique in the project: the ``ac-local-*`` and ``ac-dev-*`` servers listen there.
    mcp_runtimes: list[str] = dataclasses.field(default_factory=list)  #: For an agent: the names of the MCP runtimes it calls, each bound in ``cdk-stack.ts``.
    # fmt: on

    @property
    def slug(self) -> str:
        """
        The runtime's name in task names, such as ``my-mcp`` for ``MyMcp``.
        """
        return re.sub(r"(?<!^)(?=[A-Z])", "-", self.name).lower()


def get_runtime_specs(config: Config) -> list[RuntimeSpec]:
    """
    Every runtime of the project. To add one: its names in the config, its
    runtime module, and an entry here; then ``mise run gen-env-tasks`` writes
    its tasks. Local ports are unusual on purpose (18733, 18734, ...), so a
    listener there is almost surely a leftover server of this project.
    """
    return [
        RuntimeSpec(
            name=config.agentcore_runtime_name_audit_mcp,
            module="runtimes.audit_mcp",
            protocol=RuntimeProtocolEnum.MCP,
            sample_payload={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "list_sessions", "arguments": {"limit": 3}},
            },
            local_port=18733,
        ),
        RuntimeSpec(
            name=config.agentcore_runtime_name_audit_agent,
            module="runtimes.audit_agent",
            protocol=RuntimeProtocolEnum.HTTP,
            sample_payload={
                "prompt": (
                    "Audit session ses_e70a629f1a7e. Is anything in it a security risk?"
                ),
            },
            local_port=18734,
            mcp_runtimes=[config.agentcore_runtime_name_audit_mcp],
        ),
    ]
