# -*- coding: utf-8 -*-

from agent_app.cdk.stack_enum import StackEnum

import aws_cdk as cdk

from agent_app.config.api import Config
from agent_app.one.api import One
from agent_app.cdk.stack_ctx_enum import (
    StackCtxEnum,
)
from agent_app.cdk.stack_ctx_enum import (
    list_entry_names,
)


def test_entries_match_stack_ctx_enum():
    """
    Layer 2 has exactly the entries of layer 1, in the same order.
    """
    assert list_entry_names(StackEnum) == list_entry_names(StackCtxEnum)


def test_synth(config: Config, tmp_path):
    """
    Every stack is synthesized under its stack name.
    """
    one = One()
    one.config = config
    se = StackEnum(app=cdk.App(outdir=str(tmp_path)), one=one)
    se.synth()
    names = sorted(p.name for p in tmp_path.glob("*.template.json"))
    assert names == [
        "my-project-dev-agentcore-deps.template.json",
        "my-project-dev-web-invoker.template.json",
    ]
    assert se.get("agentcore_deps") is se.agentcore_deps
    assert se.get_all() == [se.agentcore_deps, se.web_invoker]


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.cdk.stack_enum",
        preview=False,
    )
