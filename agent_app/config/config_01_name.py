# -*- coding: utf-8 -*-

"""
Every AWS resource name of the project, with its console URL and ARN.

Names are built here, never in the CDK code, so stacks, scripts, and tests all
refer to the same value (``one.config.ssm_param_name_config``) instead of
repeating a string template.

Naming pattern: ``<resource type>_<attribute>_<short name>``, such as
``cft_stack_name_agentcore_deps``, ``cft_stack_url_agentcore_deps``, ``ssm_param_arn_config``.
CloudFormation stacks have no ARN property, because the ARN ends in a random ID
assigned at creation.
"""

from __future__ import annotations

import typing as T
import urllib.parse
from functools import cached_property

if T.TYPE_CHECKING:  # pragma: no cover
    from .config_00_main import Config


class ConfigNameMixin:
    """
    Resource names, console URLs, and ARNs derived from the config values.
    """

    # --------------------------------------------------------------------------
    # Prefixes
    # --------------------------------------------------------------------------
    @cached_property
    def project_name_snake(self: Config) -> str:
        """
        Project name in snake_case, such as ``my_project``.
        """
        return self.project_name.replace("-", "_")

    @cached_property
    def project_name_slug(self: Config) -> str:
        """
        Project name in slug-case, such as ``my-project``.
        """
        return self.project_name_snake.replace("_", "-")

    @cached_property
    def prefix_name_slug(self: Config) -> str:
        """
        Prefix of every resource name of this environment, such as ``my-project-dev``.
        """
        return f"{self.project_name_slug}-{self.env_name}"

    # --------------------------------------------------------------------------
    # CloudFormation stacks
    # --------------------------------------------------------------------------
    def get_cft_stack_name(self: Config, short_name: str) -> str:
        """
        The name of a stack, ``<prefix_name_slug>-<short_name>``; also its construct ID.
        """
        return f"{self.prefix_name_slug}-{short_name}"

    def get_cft_stack_url(self: Config, stack_name: str) -> str:
        """
        The CloudFormation console URL of the stack, found by its name, so it needs
        no stack ARN (which ends in an ID assigned at creation) and works before the
        stack exists.
        """
        return (
            f"https://{self.aws_region}.console.aws.amazon.com/cloudformation/home"
            f"?region={self.aws_region}#/stacks/stackinfo?filteringText={stack_name}"
            f"&filteringStatus=active&viewNested=true"
        )

    @cached_property
    def cft_stack_name_agentcore_deps(self: Config) -> str:
        """
        Name of the stack of what the AgentCore runtimes depend on but is not
        AgentCore, such as ``my-project-dev-agentcore-deps``; deploy it before
        ``ac-deploy-<env>``.
        """
        return self.get_cft_stack_name("agentcore-deps")

    @cached_property
    def cft_stack_url_agentcore_deps(self: Config) -> str:
        """
        Console URL of :attr:`cft_stack_name_agentcore_deps`.
        """
        return self.get_cft_stack_url(self.cft_stack_name_agentcore_deps)

    @cached_property
    def cft_stack_name_web_invoker(self: Config) -> str:
        """
        Name of the stack of what lets the hosted web app call the AuditAgent
        runtime, such as ``my-project-dev-web-invoker``.
        """
        return self.get_cft_stack_name("web-invoker")

    @cached_property
    def cft_stack_url_web_invoker(self: Config) -> str:
        """
        Console URL of :attr:`cft_stack_name_web_invoker`.
        """
        return self.get_cft_stack_url(self.cft_stack_name_web_invoker)

    @cached_property
    def cft_stack_name_agentcore(self: Config) -> str:
        """
        Name of the stack the AgentCore CLI deploys from ``agentcore/``, such as
        ``AgentCore-MyProject-dev``. The CLI's CDK app names it
        ``AgentCore-<project>-<target>``, with ``_`` turned into ``-``.
        """
        name = f"AgentCore-{self.agentcore_project_name}-{self.agentcore_target_name}"
        return name.replace("_", "-")

    @cached_property
    def cft_stack_url_agentcore(self: Config) -> str:
        """
        Console URL of :attr:`cft_stack_name_agentcore`.
        """
        return self.get_cft_stack_url(self.cft_stack_name_agentcore)

    # --------------------------------------------------------------------------
    # IAM roles
    # --------------------------------------------------------------------------

    def get_iam_role_url(self: Config, role_name: str) -> str:
        """
        The console URL of an IAM role, given its name.
        """
        return (
            f"https://{self.aws_region}.console.aws.amazon.com/iam/home"
            f"?region={self.aws_region}#/roles/details/{role_name}"
        )

    @cached_property
    def iam_role_name_web_invoker(self: Config) -> str:
        """
        Name of the role the hosted web app assumes to call the AuditAgent
        runtime, such as ``my-project-dev-us-east-1-web-invoker``. IAM is
        global, so the name includes the region.
        """
        return f"{self.prefix_name_slug}-{self.aws_region}-web-invoker"

    @cached_property
    def iam_role_arn_web_invoker(self: Config) -> str:
        """
        ARN of :attr:`iam_role_name_web_invoker`; the value of ``AWS_ROLE_ARN``
        on the hosting platform.
        """
        return (
            f"arn:aws:iam::{self.aws_account_id}:role/{self.iam_role_name_web_invoker}"
        )

    @cached_property
    def iam_role_url_web_invoker(self: Config) -> str:
        """
        Console URL of :attr:`iam_role_name_web_invoker`.
        """
        return self.get_iam_role_url(self.iam_role_name_web_invoker)

    # --------------------------------------------------------------------------
    # Vercel OIDC (how the hosted web app proves to AWS who it is)
    # --------------------------------------------------------------------------
    @cached_property
    def vercel_oidc_issuer(self: Config) -> str:
        """
        The issuer of the OIDC tokens Vercel gives the team's deployments,
        without the scheme, such as ``oidc.vercel.com/acme-team`` (Vercel's
        "team" issuer mode, its default). IAM names the provider, and prefixes
        the condition keys of a trust policy, with it.
        """
        return f"oidc.vercel.com/{self.vercel_team_slug}"

    @cached_property
    def vercel_oidc_issuer_url(self: Config) -> str:
        """
        :attr:`vercel_oidc_issuer` as the URL the IAM OIDC provider is created with.
        """
        return f"https://{self.vercel_oidc_issuer}"

    @cached_property
    def vercel_oidc_audience(self: Config) -> str:
        """
        The ``aud`` claim of those tokens, such as ``https://vercel.com/acme-team``.
        """
        return f"https://vercel.com/{self.vercel_team_slug}"

    @cached_property
    def vercel_oidc_subject(self: Config) -> str:
        """
        The ``sub`` claim of the token of a production deployment of the web
        app's Vercel project, such as
        ``owner:acme-team:project:my-project:environment:production``. Preview
        and development deployments have another one, so they cannot assume
        the web invoker role.
        """
        return (
            f"owner:{self.vercel_team_slug}:project:{self.vercel_project_name}"
            ":environment:production"
        )

    # --------------------------------------------------------------------------
    # IAM policies
    # --------------------------------------------------------------------------
    @cached_property
    def iam_policy_name_agentcore_runtime(self: Config) -> str:
        """
        Name of the managed policy attached to the execution role of every
        AgentCore runtime, such as ``my-project-dev-us-east-1-agentcore-runtime``.
        IAM is global, so the name includes the region.
        """
        return f"{self.prefix_name_slug}-{self.aws_region}-agentcore-runtime"

    @cached_property
    def iam_policy_arn_agentcore_runtime(self: Config) -> str:
        """
        ARN of :attr:`iam_policy_name_agentcore_runtime`; ``agentcore.json`` lists
        it in ``additionalPolicies`` of every runtime.
        """
        return (
            f"arn:aws:iam::{self.aws_account_id}:policy"
            f"/{self.iam_policy_name_agentcore_runtime}"
        )

    @cached_property
    def iam_policy_url_agentcore_runtime(self: Config) -> str:
        """
        Console URL of :attr:`iam_policy_name_agentcore_runtime`.
        """
        quoted_arn = urllib.parse.quote(self.iam_policy_arn_agentcore_runtime, safe="")
        return f"https://us-east-1.console.aws.amazon.com/iam/home#/policies/details/{quoted_arn}"

    # --------------------------------------------------------------------------
    # DynamoDB tables
    # --------------------------------------------------------------------------
    @cached_property
    def dynamodb_table_name_chat_daily_count(self: Config) -> str:
        """
        Name of the table in which the hosted web app counts the questions of
        a day, such as ``my-project-dev-chat-daily-count``.
        """
        return f"{self.prefix_name_slug}-chat-daily-count"

    @cached_property
    def dynamodb_table_arn_chat_daily_count(self: Config) -> str:
        """
        ARN of :attr:`dynamodb_table_name_chat_daily_count`; the value of
        ``CHAT_DAILY_TABLE_ARN`` on the hosting platform.
        """
        return (
            f"arn:aws:dynamodb:{self.aws_region}:{self.aws_account_id}"
            f":table/{self.dynamodb_table_name_chat_daily_count}"
        )

    # --------------------------------------------------------------------------
    # CloudWatch log groups
    # --------------------------------------------------------------------------
    def get_cloudwatch_log_group_url(self: Config, log_group_name: str) -> str:
        """
        The console URL of a CloudWatch log group, given its name.
        """
        # the console escapes "/" in the log group name as "$252F"
        name = log_group_name.replace("/", "$252F")
        return (
            f"https://{self.aws_region}.console.aws.amazon.com/cloudwatch/home"
            f"?region={self.aws_region}#logsV2:log-groups/log-group/{name}"
        )

    # --------------------------------------------------------------------------
    # SSM parameters
    # --------------------------------------------------------------------------
    def get_ssm_param_url(self: Config, name: str) -> str:
        """
        The console URL of an SSM parameter, given its name (which starts with ``/``).
        """
        return (
            f"https://{self.aws_region}.console.aws.amazon.com/systems-manager"
            f"/parameters{name}/description?region={self.aws_region}&tab=Table"
        )

    def get_ssm_param_arn(self: Config, name: str) -> str:
        """
        The ARN of an SSM parameter, given its name (which starts with ``/``).
        """
        return f"arn:aws:ssm:{self.aws_region}:{self.aws_account_id}:parameter{name}"

    @cached_property
    def ssm_param_name_config(self: Config) -> str:
        """
        Name of the parameter that holds the whole config of this environment as
        JSON, such as ``/my-project-dev/config``; written by ``mise run config-deploy-<env>``.
        """
        return f"/{self.prefix_name_slug}/config"

    @cached_property
    def ssm_param_url_config(self: Config) -> str:
        """
        Console URL of :attr:`ssm_param_name_config`.
        """
        return self.get_ssm_param_url(self.ssm_param_name_config)

    @cached_property
    def ssm_param_arn_config(self: Config) -> str:
        """
        ARN of :attr:`ssm_param_name_config`.
        """
        return self.get_ssm_param_arn(self.ssm_param_name_config)

    # --------------------------------------------------------------------------
    # AgentCore (the agentcore/ project, deployed by the AgentCore CLI)
    # --------------------------------------------------------------------------
    @cached_property
    def agentcore_target_name(self: Config) -> str:
        """
        The AgentCore CLI deployment target of this environment, named after it,
        such as ``dev``. The CLI puts the target in every physical name, so
        every AgentCore resource name contains the environment.
        """
        return self.env_name

    def get_agentcore_runtime_physical_name(self: Config, name: str) -> str:
        """
        The name AWS knows a runtime by, ``<project>_<target>_<name>``, such as
        ``MyProject_dev_AuditMcp``; ``name`` is its name in ``agentcore.json``.

        :raises ValueError: if longer than the 48 characters AgentCore allows.
        """
        target = self.agentcore_target_name.replace("-", "_")
        physical_name = f"{self.agentcore_project_name}_{target}_{name}"
        if len(physical_name) > 48:
            raise ValueError(
                f"runtime name {physical_name!r} is longer than 48 characters, "
                "shorten agentcore_project_name or the runtime name"
            )
        return physical_name

    def get_agentcore_runtime_url(self: Config, runtime_id: str) -> str:
        """
        The AgentCore console URL of a deployed runtime, given its ID, such as
        ``MyProject_dev_AuditMcp-abc``: the physical name plus a suffix
        AWS assigns at deploy time, so it is looked up, never built.
        """
        return (
            f"https://{self.aws_region}.console.aws.amazon.com"
            f"/bedrock-agentcore/agents/{runtime_id}"
        )

    def get_agentcore_runtime_arn_pattern(self: Config, physical_name: str) -> str:
        """
        An IAM resource pattern for a runtime given its physical name, such as
        ``arn:aws:bedrock-agentcore:us-east-1:111122223333:runtime/MyProject_dev_AuditAgent-*``.
        The runtime's ID is the physical name plus a suffix AWS assigns at
        deploy time, so a policy written before the deploy cannot name it. The
        pattern also matches the runtime's endpoints
        (``<runtime ARN>/runtime-endpoint/<name>``), which an invocation is
        authorized against as well.
        """
        return (
            f"arn:aws:bedrock-agentcore:{self.aws_region}:{self.aws_account_id}"
            f":runtime/{physical_name}-*"
        )

    @cached_property
    def agentcore_runtime_name_audit_mcp(self: Config) -> str:
        """
        Name of the audit MCP server runtime in ``agentcore.json``, ``AuditMcp``.
        """
        return "AuditMcp"

    @cached_property
    def agentcore_runtime_physical_name_audit_mcp(self: Config) -> str:
        """
        Physical name of :attr:`agentcore_runtime_name_audit_mcp`,
        such as ``MyProject_dev_AuditMcp``.
        """
        return self.get_agentcore_runtime_physical_name(
            self.agentcore_runtime_name_audit_mcp
        )

    @cached_property
    def agentcore_runtime_name_audit_agent(self: Config) -> str:
        """
        Name of the audit agent runtime in ``agentcore.json``, ``AuditAgent``.
        """
        return "AuditAgent"

    @cached_property
    def agentcore_runtime_physical_name_audit_agent(self: Config) -> str:
        """
        Physical name of :attr:`agentcore_runtime_name_audit_agent`,
        such as ``MyProject_dev_AuditAgent``.
        """
        return self.get_agentcore_runtime_physical_name(
            self.agentcore_runtime_name_audit_agent
        )

    @cached_property
    def agentcore_runtime_arn_pattern_audit_agent(self: Config) -> str:
        """
        IAM resource pattern of :attr:`agentcore_runtime_physical_name_audit_agent`
        and its endpoints.
        """
        return self.get_agentcore_runtime_arn_pattern(
            self.agentcore_runtime_physical_name_audit_agent
        )
