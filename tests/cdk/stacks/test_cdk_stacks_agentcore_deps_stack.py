# -*- coding: utf-8 -*-

"""
Synth test of the agentcore_deps stack: create it through ``StackEnum``, the way
``cdk/cdk_app.py`` does, and check the runtime policy, by name, can read only the
config parameter.
"""

from agent_app.cdk.stacks.agentcore_deps_stack import (
    AgentCoreDepsStack,
)

import aws_cdk as cdk
from aws_cdk.assertions import Template

from agent_app.config.api import Config
from agent_app.one.api import One
from agent_app.cdk.stack_enum import StackEnum


def test_synth(config: Config):
    one = One()
    one.config = config
    stack_enum = StackEnum(app=cdk.App(), one=one)
    assert isinstance(stack_enum.agentcore_deps, AgentCoreDepsStack)
    template = Template.from_stack(stack_enum.agentcore_deps)
    template.has_resource_properties(
        "AWS::IAM::ManagedPolicy",
        {
            "ManagedPolicyName": config.iam_policy_name_agentcore_runtime,
            "PolicyDocument": {
                "Statement": [
                    {
                        "Action": "ssm:GetParameter",
                        "Effect": "Allow",
                        "Resource": config.ssm_param_arn_config,
                    }
                ],
            },
        },
    )


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.cdk.stacks.agentcore_deps_stack",
        preview=False,
    )
