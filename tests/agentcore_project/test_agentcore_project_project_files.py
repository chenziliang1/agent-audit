# -*- coding: utf-8 -*-

from agent_app.agentcore_project.project_files import (
    get_runtime_env_vars,
)
from agent_app.agentcore_project.project_files import (
    build_agentcore_json,
)
from agent_app.agentcore_project.project_files import (
    build_empty_agentcore_json,
)
from agent_app.agentcore_project.project_files import (
    build_aws_targets_json,
)
from agent_app.agentcore_project.project_files import (
    write_json,
)

import json

from agent_app.paths import path_enum
from agent_app.config.api import Config
from agent_app.agentcore_project.registry import (
    get_runtime_specs,
)


def test_get_runtime_env_vars(config: Config):
    assert get_runtime_env_vars(config) == {
        "IS_AGENTCORE_RUNTIME": "true",
        "ENV_NAME": "dev",
        "CONFIG_SSM_PARAM_NAME": "/my-project-dev/config",
    }


def test_build_agentcore_json(config: Config):
    data = build_agentcore_json(config)
    assert data["name"] == "MyProject"
    assert data["version"] == 2
    assert data["managedBy"] == "CDK"
    assert data["runtimes"][0]["protocol"] == "MCP"
    assert data["runtimes"][0]["runtimeVersion"] == "PYTHON_3_12"
    assert data["runtimes"][0]["codeLocation"] == "agentcore_app/AuditMcp"
    assert data["runtimes"][1]["protocol"] == "HTTP"
    for runtime in data["runtimes"]:
        assert {"name": "ENV_NAME", "value": "dev"} in runtime["envVars"]
        assert runtime["additionalPolicies"] == [
            "arn:aws:iam::111122223333:policy/my-project-dev-us-east-1-agentcore-runtime"
        ]


def test_cdk_stack_ts_uses_the_runtime_names():
    """
    cdk-stack.ts has a bind() line for every MCP runtime an agent calls, by the
    names the config gives them. An MCP runtime no agent calls has none.
    """
    config = Config.load_from_local_config_file(env_name="dev")
    content = path_enum.path_agentcore_cdk_stack_ts.read_text(encoding="utf-8")
    lines = [
        f"runtime('{name}').bind(this.application.runtime('{spec.name}'))"
        for spec in get_runtime_specs(config)
        for name in spec.mcp_runtimes
    ]
    assert lines
    for line in lines:
        assert line in content


def test_build_empty_agentcore_json(config: Config):
    """The shape `agentcore create` writes for an empty project: no runtimes key."""
    assert build_empty_agentcore_json(config) == {
        "name": "MyProject",
        "version": 2,
        "managedBy": "CDK",
    }


def test_cdk_stack_ts_synthesizes_an_empty_project():
    """bind() is skipped when the project declares no runtime (ac-down-<env>)."""
    content = path_enum.path_agentcore_cdk_stack_ts.read_text(encoding="utf-8")
    assert "if (this.application.runtimes.size > 0)" in content


def test_build_aws_targets_json(config: Config):
    assert build_aws_targets_json(config) == [
        {
            "name": "dev",
            "description": "The dev environment",
            "account": "111122223333",
            "region": "us-east-1",
        }
    ]


def test_write_json(tmp_path):
    path = tmp_path / "data.json"
    assert write_json(path, {"a": 1}) is True
    assert write_json(path, {"a": 1}) is False
    assert json.loads(path.read_text()) == {"a": 1}


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.agentcore_project.project_files",
        preview=False,
    )
