# -*- coding: utf-8 -*-

from agent_app.one import api


def test():
    _ = api
    _ = api.One
    _ = api.one


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.one.api",
        preview=False,
    )
