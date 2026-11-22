# -*- coding: utf-8 -*-

from agent_app.one.one_01_config import (
    OneConfigMixin,
)

import moto
import boto3

from agent_app.config.api import Config
from agent_app.one.api import One


def test_config():
    one = One()
    assert isinstance(one, OneConfigMixin)
    assert isinstance(one.config, Config)
    assert one.config.project_name == "agent_audit"
    assert one.config.env_name == one.env.current_env_name
    # cached: built once
    assert one.config is one.config


def test_config_on_agentcore(config: Config, monkeypatch):
    """
    On a deployed runtime, ``one.config`` reads the SSM parameter with ``one.ssm_client``.
    """
    monkeypatch.setenv("IS_AGENTCORE_RUNTIME", "true")
    monkeypatch.setenv("CONFIG_SSM_PARAM_NAME", config.ssm_param_name_config)
    with moto.mock_aws():
        one = One()
        one.ssm_client = boto3.client("ssm", region_name="us-east-1")
        one.ssm_client.put_parameter(
            Name=config.ssm_param_name_config,
            Value=config.model_dump_json(),
            Type="SecureString",
        )
        assert one.config == config


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.one.one_01_config",
        preview=False,
    )
