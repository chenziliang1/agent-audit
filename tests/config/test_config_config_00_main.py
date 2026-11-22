# -*- coding: utf-8 -*-

from agent_app.config.config_00_main import Config

import pytest

import moto
import boto3
from pydantic import ValidationError


class TestConfig:
    def test_validation(self):
        with pytest.raises(ValidationError):
            Config(project_name="my_project")

    def test_load_from_local_config_file(self, tmp_path):
        """
        Later files override earlier ones, and a missing secret file is skipped.
        """
        (tmp_path / "config-shared.json5").write_text(
            '{project_name: "a", aws_region: "shared", agentcore_project_name: "A", audit_agent_model_id: "m", audit_agent_fallback_model_id: "f", vercel_team_slug: "t", vercel_project_name: "p"}'
        )
        (tmp_path / "config-dev.json5").write_text(
            "// comment\n{aws_account_id: '1', aws_region: 'dev'}"
        )
        (tmp_path / "config-dev-secret.json5").write_text(
            "{project_name: 'b', anthropic_api_key: 'k'}"
        )
        conf = Config.load_from_local_config_file(env_name="dev", dir_config=tmp_path)
        assert conf.project_name == "b"
        assert conf.env_name == "dev"
        assert conf.aws_region == "dev"
        assert conf.anthropic_api_key == "k"

    def test_api_key_is_not_printed(self, config: Config):
        """
        A printed config (a log line, a traceback) does not show the API key;
        the JSON written to the SSM SecureString parameter does carry it.
        """
        assert config.anthropic_api_key not in repr(config)
        assert config.anthropic_api_key not in str(config)
        assert config.anthropic_api_key in config.model_dump_json()

    @pytest.mark.parametrize(
        "env_name",
        [
            "dev",
            "tst",
            "prd",
        ],
    )
    def test_load(self, env_name: str):
        """
        The committed config files, plus a secret file, load for every environment.
        """
        conf = Config.load(env_name=env_name, runtime_name="local")
        assert conf.env_name == env_name
        # from the fake secret file in conftest.py, not the real one
        assert conf.aws_account_id == "111122223333"

    def test_load_from_ssm(self, config: Config, monkeypatch):
        """
        On both AgentCore runtimes, the config comes from the parameter in
        ``CONFIG_SSM_PARAM_NAME``; a missing parameter is a clear error.
        """
        with moto.mock_aws():
            ssm_client = boto3.client("ssm", region_name="us-east-1")
            name = config.ssm_param_name_config
            with pytest.raises(ValueError, match="config-deploy"):
                Config.load_from_ssm(ssm_client=ssm_client, name=name)
            ssm_client.put_parameter(
                Name=name,
                Value=config.model_dump_json(),
                Type="SecureString",
            )
            assert Config.load_from_ssm(ssm_client=ssm_client, name=name) == config
            monkeypatch.setenv("CONFIG_SSM_PARAM_NAME", name)
            for runtime_name in ["agentcore", "agentcore_local"]:
                conf = Config.load(
                    env_name="dev",
                    runtime_name=runtime_name,
                    ssm_client=ssm_client,
                )
                assert conf == config

    def test_load_error(self):
        with pytest.raises(NotImplementedError):
            Config.load(env_name="dev", runtime_name="ci")


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.config.config_00_main",
        preview=False,
    )
