# -*- coding: utf-8 -*-

from agent_app.config import api


def test():
    _ = api
    _ = api.Config


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.config.api",
        preview=False,
    )
