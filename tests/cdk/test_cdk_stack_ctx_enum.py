# -*- coding: utf-8 -*-

from agent_app.cdk.stack_ctx_enum import (
    list_entry_names,
)
from agent_app.cdk.stack_ctx_enum import (
    StackCtxEnum,
)

from agent_app.config.api import Config
from agent_app.one.api import One


def test_list_entry_names():
    assert list_entry_names(StackCtxEnum) == [
        "agentcore_deps",
        "web_invoker",
        "monitoring",
    ]


class TestStackCtxEnum:
    def test_entries(self, config: Config):
        """
        Names, account, and region come from one.config, the session is one.bsm;
        nothing calls AWS.
        """
        one = One()
        one.config = config
        stack_ctx_enum = StackCtxEnum(one=one)
        stack_ctx = stack_ctx_enum.agentcore_deps
        assert stack_ctx.construct_id == "my-project-dev-agentcore-deps"
        assert stack_ctx.stack_name == "my-project-dev-agentcore-deps"
        assert stack_ctx.aws_account_id == "111122223333"
        assert stack_ctx.aws_region == "us-east-1"
        assert stack_ctx.bsm is one.bsm

        assert stack_ctx_enum.get("agentcore_deps") is stack_ctx
        assert stack_ctx_enum.web_invoker.stack_name == "my-project-dev-web-invoker"
        assert stack_ctx_enum.monitoring.stack_name == "my-project-dev-monitoring"
        assert stack_ctx_enum.get_all() == [
            stack_ctx,
            stack_ctx_enum.web_invoker,
            stack_ctx_enum.monitoring,
        ]


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.cdk.stack_ctx_enum",
        preview=False,
    )
