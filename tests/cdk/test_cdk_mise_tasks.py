# -*- coding: utf-8 -*-

from agent_app.cdk.mise_tasks import (
    render_env_tasks_block,
)
from agent_app.cdk.mise_tasks import (
    get_stack_targets,
)


def test_render_env_tasks_block():
    """
    The cdk tasks of each stack, with the extra tasks of the environment before
    them and the tail tasks last.
    """
    block = render_env_tasks_block(
        env_stack_targets={"dev": get_stack_targets("dev")},
        env_extra_tasks={"dev": "# extra of dev"},
        tail_tasks=["# tail"],
    )
    assert block.startswith("# <env-tasks>")
    assert block.endswith("# </env-tasks>")
    assert block.index("# extra of dev") < block.index('[tasks."cdk-synth-dev-all"]')
    assert block.index('[tasks."cdk-down-dev-agentcore-deps-stack"]') < block.index(
        "# tail"
    )
    # without extras
    assert "# extra" not in render_env_tasks_block({"dev": get_stack_targets("dev")})


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.cdk.mise_tasks",
        preview=False,
    )
