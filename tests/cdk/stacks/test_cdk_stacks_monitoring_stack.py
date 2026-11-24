# -*- coding: utf-8 -*-

"""
Synth test of the monitoring stack: create it through ``StackEnum``, the way
``cdk/cdk_app.py`` does, and check what each alarm watches and whom it tells.
"""

from agent_app.cdk.stacks.monitoring_stack import (
    MonitoringStack,
)

import aws_cdk as cdk
from aws_cdk.assertions import Match
from aws_cdk.assertions import Template

from agent_app.config.api import Config
from agent_app.one.api import One
from agent_app.cdk.stack_enum import StackEnum


def runtime_alarm(alarm_name: str, metric_name: str, runtime: str) -> dict:
    """
    The properties of an alarm on a metric of one runtime, whose ARN is
    imported from the AgentCore stack.
    """
    return {
        "AlarmName": alarm_name,
        "Namespace": "AWS/Bedrock-AgentCore",
        "MetricName": metric_name,
        "Dimensions": [
            {"Name": "Name", "Value": f"MyProject_dev_{runtime}::DEFAULT"},
            {"Name": "Operation", "Value": "InvokeAgentRuntime"},
            {
                "Name": "Resource",
                "Value": {
                    "Fn::ImportValue": f"AgentCore-MyProject-dev-{runtime}-RuntimeArn",
                },
            },
        ],
    }


def test_synth(config: Config):
    one = One()
    one.config = config
    stack_enum = StackEnum(app=cdk.App(), one=one)
    assert isinstance(stack_enum.monitoring, MonitoringStack)
    template = Template.from_stack(stack_enum.monitoring)

    # one topic, and nobody subscribed by the stack
    template.has_resource_properties(
        "AWS::SNS::Topic",
        {"TopicName": "my-project-dev-alarms"},
    )
    template.resource_count_is("AWS::SNS::Subscription", 0)

    # every alarm goes off at one event in five minutes, stays quiet without
    # data, and tells the topic when it goes off, not when it recovers
    template.resource_count_is("AWS::CloudWatch::Alarm", 4)
    template.all_resources_properties(
        "AWS::CloudWatch::Alarm",
        {
            "Statistic": "Sum",
            "Period": 300,
            "EvaluationPeriods": 1,
            "Threshold": 1,
            "ComparisonOperator": "GreaterThanOrEqualToThreshold",
            "TreatMissingData": "notBreaching",
            "AlarmActions": [{"Ref": Match.string_like_regexp("^AlarmTopic")}],
            "OKActions": Match.absent(),
        },
    )

    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        runtime_alarm("my-project-dev-audit-agent-errors", "Errors", "AuditAgent"),
    )
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        runtime_alarm("my-project-dev-audit-mcp-errors", "Errors", "AuditMcp"),
    )
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        runtime_alarm(
            "my-project-dev-audit-agent-throttles", "Throttles", "AuditAgent"
        ),
    )
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "AlarmName": "my-project-dev-chat-daily-limit",
            "Namespace": "AWS/DynamoDB",
            "MetricName": "ConditionalCheckFailedRequests",
            "Dimensions": [
                {"Name": "TableName", "Value": "my-project-dev-chat-daily-count"},
            ],
        },
    )


if __name__ == "__main__":
    from agent_app.tests import run_cov_test

    run_cov_test(
        __file__,
        "agent_app.cdk.stacks.monitoring_stack",
        preview=False,
    )
