# -*- coding: utf-8 -*-

"""
Synth test of the web_invoker stack: create it through ``StackEnum``, the way
``cdk/cdk_app.py`` does, and check who may assume the role, what it may do, and
the table it counts in.
"""

from agent_app.cdk.stacks.web_invoker_stack import (
    WebInvokerStack,
)

import aws_cdk as cdk
from aws_cdk.assertions import Match
from aws_cdk.assertions import Template

from agent_app.config.api import Config
from agent_app.one.api import One
from agent_app.cdk.stack_enum import StackEnum


def test_synth(config: Config):
    one = One()
    one.config = config
    stack_enum = StackEnum(app=cdk.App(), one=one)
    assert isinstance(stack_enum.web_invoker, WebInvokerStack)
    template = Template.from_stack(stack_enum.web_invoker)
    template.has_resource_properties(
        "AWS::IAM::OIDCProvider",
        {
            "Url": "https://oidc.vercel.com/acme-team",
            "ClientIdList": ["https://vercel.com/acme-team"],
        },
    )
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "RoleName": config.iam_role_name_web_invoker,
            # only a production deployment of the one Vercel project
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRoleWithWebIdentity",
                        "Effect": "Allow",
                        "Principal": {"Federated": Match.any_value()},
                        "Condition": {
                            "StringEquals": {
                                "oidc.vercel.com/acme-team:aud": "https://vercel.com/acme-team",
                                "oidc.vercel.com/acme-team:sub": "owner:acme-team:project:my-project:environment:production",
                            },
                        },
                    }
                ],
            },
            # and only to invoke the one runtime and count a question
            "Policies": [
                {
                    "PolicyName": "invoke-audit-agent",
                    "PolicyDocument": {
                        "Statement": [
                            {
                                "Action": "bedrock-agentcore:InvokeAgentRuntime",
                                "Effect": "Allow",
                                "Resource": config.agentcore_runtime_arn_pattern_audit_agent,
                            }
                        ],
                    },
                },
                {
                    "PolicyName": "count-chat-questions",
                    "PolicyDocument": {
                        "Statement": [
                            {
                                "Action": "dynamodb:UpdateItem",
                                "Effect": "Allow",
                                "Resource": {
                                    "Fn::GetAtt": [Match.any_value(), "Arn"],
                                },
                            }
                        ],
                    },
                },
            ],
        },
    )
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "TableName": config.dynamodb_table_name_chat_daily_count,
            "KeySchema": [{"AttributeName": "day", "KeyType": "HASH"}],
            "BillingMode": "PAY_PER_REQUEST",
            "TimeToLiveSpecification": {
                "AttributeName": "expires_at",
                "Enabled": True,
            },
        },
    )
    template.has_resource("AWS::DynamoDB::Table", {"DeletionPolicy": "Delete"})


def test_synth_without_the_oidc_provider(config: Config):
    """
    In an environment that does not own the Vercel team's OIDC provider, the
    stack creates none and the role trusts the existing one by its ARN.
    """
    one = One()
    one.config = Config(**{**config.model_dump(), "env_name": "prd"})
    stack_enum = StackEnum(app=cdk.App(), one=one)
    template = Template.from_stack(stack_enum.web_invoker)
    template.resource_count_is("AWS::IAM::OIDCProvider", 0)
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "RoleName": "my-project-prd-us-east-1-web-invoker",
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRoleWithWebIdentity",
                        "Effect": "Allow",
                        "Principal": {
                            "Federated": "arn:aws:iam::111122223333:oidc-provider/oidc.vercel.com/acme-team",
                        },
                        "Condition": Match.any_value(),
                    }
                ],
            },
        },
    )
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {"TableName": "my-project-prd-chat-daily-count"},
    )


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.cdk.stacks.web_invoker_stack",
        preview=False,
    )
