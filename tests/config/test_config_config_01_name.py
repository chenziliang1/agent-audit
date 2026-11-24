# -*- coding: utf-8 -*-

from agent_app.config.config_01_name import (
    ConfigNameMixin,
)

import pytest

from agent_app.env import EnvNameEnum
from agent_app.config.api import Config


def test_names(config: Config):
    """
    Every resource name, so a rename that would break what depends on it fails here.
    One name per line, kept unwrapped by ``fmt: off``, so the list reads like a table.
    """
    assert isinstance(config, ConfigNameMixin)
    # fmt: off
    # prefixes
    assert config.project_name_snake == "my_project"
    assert config.project_name_slug == "my-project"
    assert config.prefix_name_slug == "my-project-dev"
    # stacks
    assert config.cft_stack_name_agentcore_deps == "my-project-dev-agentcore-deps"
    assert config.cft_stack_url_agentcore_deps == "https://us-east-1.console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/stackinfo?filteringText=my-project-dev-agentcore-deps&filteringStatus=active&viewNested=true"
    assert config.cft_stack_name_web_invoker == "my-project-dev-web-invoker"
    assert config.cft_stack_url_web_invoker == "https://us-east-1.console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/stackinfo?filteringText=my-project-dev-web-invoker&filteringStatus=active&viewNested=true"
    assert config.cft_stack_name_monitoring == "my-project-dev-monitoring"
    assert config.cft_stack_url_monitoring == "https://us-east-1.console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/stackinfo?filteringText=my-project-dev-monitoring&filteringStatus=active&viewNested=true"
    # iam roles
    assert config.iam_role_name_web_invoker == "my-project-dev-us-east-1-web-invoker"
    assert config.iam_role_arn_web_invoker == "arn:aws:iam::111122223333:role/my-project-dev-us-east-1-web-invoker"
    assert config.iam_role_url_web_invoker == "https://us-east-1.console.aws.amazon.com/iam/home?region=us-east-1#/roles/details/my-project-dev-us-east-1-web-invoker"
    # vercel oidc
    assert config.vercel_oidc_issuer == "oidc.vercel.com/acme-team"
    assert config.vercel_oidc_issuer_url == "https://oidc.vercel.com/acme-team"
    assert config.iam_oidc_provider_arn_vercel == "arn:aws:iam::111122223333:oidc-provider/oidc.vercel.com/acme-team"
    assert config.vercel_oidc_audience == "https://vercel.com/acme-team"
    assert config.vercel_oidc_subject == "owner:acme-team:project:my-project:environment:production"
    # iam policies
    assert config.iam_policy_name_agentcore_runtime == "my-project-dev-us-east-1-agentcore-runtime"
    assert config.iam_policy_arn_agentcore_runtime == "arn:aws:iam::111122223333:policy/my-project-dev-us-east-1-agentcore-runtime"
    assert config.iam_policy_url_agentcore_runtime == "https://us-east-1.console.aws.amazon.com/iam/home#/policies/details/arn%3Aaws%3Aiam%3A%3A111122223333%3Apolicy%2Fmy-project-dev-us-east-1-agentcore-runtime"
    # dynamodb tables
    assert config.dynamodb_table_name_chat_daily_count == "my-project-dev-chat-daily-count"
    assert config.dynamodb_table_arn_chat_daily_count == "arn:aws:dynamodb:us-east-1:111122223333:table/my-project-dev-chat-daily-count"
    # sns topics
    assert config.sns_topic_name_alarms == "my-project-dev-alarms"
    assert config.sns_topic_arn_alarms == "arn:aws:sns:us-east-1:111122223333:my-project-dev-alarms"
    # cloudwatch alarms
    assert config.get_cloudwatch_alarm_name("widget-errors") == "my-project-dev-widget-errors"
    # ssm
    assert config.ssm_param_name_config == "/my-project-dev/config"
    assert config.ssm_param_arn_config == "arn:aws:ssm:us-east-1:111122223333:parameter/my-project-dev/config"
    assert "/parameters/my-project-dev/config/" in config.ssm_param_url_config
    # agentcore
    assert config.cft_stack_name_agentcore == "AgentCore-MyProject-dev"
    assert config.cft_stack_url_agentcore == "https://us-east-1.console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/stackinfo?filteringText=AgentCore-MyProject-dev&filteringStatus=active&viewNested=true"
    assert config.get_agentcore_export_name("AuditAgent", "RuntimeArn") == "AgentCore-MyProject-dev-AuditAgent-RuntimeArn"
    assert config.agentcore_target_name == "dev"
    assert config.agentcore_runtime_name_audit_mcp == "AuditMcp"
    assert config.agentcore_runtime_physical_name_audit_mcp == "MyProject_dev_AuditMcp"
    assert config.agentcore_runtime_name_audit_agent == "AuditAgent"
    assert config.agentcore_runtime_physical_name_audit_agent == "MyProject_dev_AuditAgent"
    assert config.agentcore_runtime_arn_pattern_audit_agent == "arn:aws:bedrock-agentcore:us-east-1:111122223333:runtime/MyProject_dev_AuditAgent-*"
    # urls of what is named at deploy time
    assert config.get_agentcore_runtime_url("MyProject_dev_AuditAgent-abc") == "https://us-east-1.console.aws.amazon.com/bedrock-agentcore/agents/MyProject_dev_AuditAgent-abc"
    assert config.get_iam_role_url("my-role") == "https://us-east-1.console.aws.amazon.com/iam/home?region=us-east-1#/roles/details/my-role"
    assert config.get_cloudwatch_log_group_url("/aws/x-DEFAULT") == "https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Fx-DEFAULT"
    # fmt: on


def test_agentcore_runtime_physical_name_too_long(config: Config):
    with pytest.raises(ValueError, match="longer than 48 characters"):
        config.get_agentcore_runtime_physical_name("X" * 40)


@pytest.mark.parametrize("env_name", [env_name.value for env_name in EnvNameEnum])
def test_agentcore_runtime_physical_names_fit(env_name: str):
    """
    With the committed config files, every runtime's physical name fits the
    48 characters AgentCore allows, in every environment.
    """
    config = Config.load_from_local_config_file(env_name=env_name)
    prefix = "agentcore_runtime_physical_name_"
    names = [name for name in dir(type(config)) if name.startswith(prefix)]
    assert names
    for name in names:
        assert len(getattr(config, name)) <= 48


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.config.config_01_name",
        preview=False,
    )
