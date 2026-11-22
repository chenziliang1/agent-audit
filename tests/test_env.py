# -*- coding: utf-8 -*-

from agent_app.env import ENV_NAME_VAR
from agent_app.env import EnvNameEnum
from agent_app.env import Env

import pytest


class TestEnv:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, EnvNameEnum.dev),
            ("", EnvNameEnum.dev),
            ("prd", EnvNameEnum.prd),
        ],
    )
    def test_get_current_env_name(self, monkeypatch, value, expected):
        if value is None:
            monkeypatch.delenv(ENV_NAME_VAR, raising=False)
        else:
            monkeypatch.setenv(ENV_NAME_VAR, value)
        env = Env()
        assert env.get_current_env_name() is expected
        assert env.current_env_name == expected.value

    def test_get_current_env_name_error(self, monkeypatch):
        monkeypatch.setenv(ENV_NAME_VAR, "qa")
        with pytest.raises(ValueError):
            Env().get_current_env_name()


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.env",
        preview=False,
    )
