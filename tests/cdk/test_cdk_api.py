# -*- coding: utf-8 -*-

from agent_app.cdk import api


def test():
    _ = api
    _ = api.AgentCoreDepsStack
    _ = api.WebInvokerStack
    _ = api.StackCtxEnum
    _ = api.StackEnum


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.cdk.api",
        preview=False,
    )
