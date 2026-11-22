# -*- coding: utf-8 -*-

from agent_app.one.one_00_main import One
from agent_app.one.one_00_main import one

from agent_app.env import env
from agent_app.runtime import runtime


def test_one():
    """
    ``one`` exposes the module-level env and runtime singletons, not copies.
    """
    assert isinstance(one, One)
    assert one.env is env
    assert one.runtime is runtime


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.one.one_00_main",
        preview=False,
    )
