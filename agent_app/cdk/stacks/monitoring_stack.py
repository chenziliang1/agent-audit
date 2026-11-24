# -*- coding: utf-8 -*-

"""
The monitoring stack: the alarms that say the product is failing or being used
up, and the topic they notify.

Nobody watches a console. Four things are worth a message, and each is a metric
AWS already records, so the stack creates no code and no metric of its own:

- an invocation of the ``AuditAgent`` runtime failed (the agent raised, the
  model's API key stopped working, the runtime did not start);
- an invocation of the ``AuditMcp`` runtime failed (the agent's tools);
- AgentCore throttled the ``AuditAgent`` runtime;
- the web app turned a question away because the day's limit was reached: the
  conditional update of ``lib/agent/daily-count.ts`` failed its condition.

What it cannot see is a request that fails before it reaches AWS: the web app's
own checks, or the hosting platform being down.

**It names the runtimes by the exports of the AgentCore stack.** A runtime's
metrics carry its ARN, which ends in an ID AWS picks at creation, so the ARN is
imported from the stack the AgentCore CLI deploys. Two consequences:

- deploy this stack after ``ac-deploy-<env>``, never before;
- CloudFormation refuses to change or remove an export that is imported, so a
  deploy that would replace a runtime, and ``ac-down-<env>``, fail until this
  stack is destroyed first. That failure is the point: alarms that silently
  watch a runtime that no longer exists would be worse.

**Who is told is not in this stack.** The topic has no subscription here: an
e-mail address is not a setting of this project. Subscribe by hand
(``aws sns subscribe --topic-arn <config.sns_topic_arn_alarms> --protocol email
--notification-endpoint <address>``) and confirm the message AWS sends.
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_sns as sns
from constructs import Construct

from ...config.api import Config

#: The namespace AgentCore Runtime publishes a runtime's metrics in.
AGENTCORE_NAMESPACE = "AWS/Bedrock-AgentCore"
#: The endpoint of a runtime that ``agentcore deploy`` updates; a metric's
#: ``Name`` dimension is ``<runtime physical name>::<endpoint>``.
AGENTCORE_ENDPOINT = "DEFAULT"
#: How long one evaluation of an alarm looks back.
ALARM_PERIOD = cdk.Duration.minutes(5)


class MonitoringStack(cdk.Stack):
    """
    Takes the standard arguments of :meth:`cdk_mate.stack_ctx.StackCtx.to_stack_kwargs`
    plus the config of its environment; every name comes from the config.
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        stack_name: str,
        env: cdk.Environment,
        config: Config,
    ) -> None:
        super().__init__(
            scope=scope,
            id=id,
            stack_name=stack_name,
            env=env,
        )
        self.config = config
        self.s01_create_alarm_topic()
        self.s02_create_runtime_alarms()
        self.s03_create_daily_limit_alarm()

    def s01_create_alarm_topic(self) -> None:
        """
        Create the topic every alarm notifies. It starts without a subscriber.
        """
        self.alarm_topic = sns.Topic(
            self,
            "AlarmTopic",
            topic_name=self.config.sns_topic_name_alarms,
            display_name=f"{self.config.prefix_name_slug} alarms",
        )

    def new_alarm(
        self,
        id: str,
        short_name: str,
        description: str,
        metric: cloudwatch.Metric,
    ) -> cloudwatch.Alarm:
        """
        An alarm that goes off when ``metric`` counts at least one event in a
        period, and tells the topic once, when it goes off. A period without
        data is a period in which nothing happened, not a failure: a runtime
        nobody calls publishes nothing.
        """
        alarm = cloudwatch.Alarm(
            self,
            id,
            alarm_name=self.config.get_cloudwatch_alarm_name(short_name),
            alarm_description=description,
            metric=metric,
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        alarm.add_alarm_action(cloudwatch_actions.SnsAction(self.alarm_topic))
        return alarm

    def new_runtime_metric(
        self,
        metric_name: str,
        runtime_name: str,
        runtime_physical_name: str,
    ) -> cloudwatch.Metric:
        """
        A metric of the invocations of one runtime, summed per period. The
        dimensions are the ones AgentCore publishes it with; an alarm on any
        other set of them would never see a data point.
        """
        return cloudwatch.Metric(
            namespace=AGENTCORE_NAMESPACE,
            metric_name=metric_name,
            dimensions_map={
                "Name": f"{runtime_physical_name}::{AGENTCORE_ENDPOINT}",
                "Operation": "InvokeAgentRuntime",
                "Resource": cdk.Fn.import_value(
                    self.config.get_agentcore_export_name(runtime_name, "RuntimeArn")
                ),
            },
            statistic="Sum",
            period=ALARM_PERIOD,
        )

    def s02_create_runtime_alarms(self) -> None:
        """
        Create the alarms on the two runtimes. ``Errors`` is the sum of the
        system errors and the user errors of a runtime, so it also counts a
        caller's mistake, such as a second question sent to a conversation that
        is still answering the first.
        """
        config = self.config
        env_name = config.env_name
        self.audit_agent_errors_alarm = self.new_alarm(
            id="AuditAgentErrorsAlarm",
            short_name="audit-agent-errors",
            description=(
                f"An invocation of the AuditAgent runtime of {env_name} failed: "
                "a question got no answer. Read the runtime's log group."
            ),
            metric=self.new_runtime_metric(
                metric_name="Errors",
                runtime_name=config.agentcore_runtime_name_audit_agent,
                runtime_physical_name=config.agentcore_runtime_physical_name_audit_agent,
            ),
        )
        self.audit_mcp_errors_alarm = self.new_alarm(
            id="AuditMcpErrorsAlarm",
            short_name="audit-mcp-errors",
            description=(
                f"An invocation of the AuditMcp runtime of {env_name} failed: "
                "the agent could not use one of its tools. Read the runtime's log group."
            ),
            metric=self.new_runtime_metric(
                metric_name="Errors",
                runtime_name=config.agentcore_runtime_name_audit_mcp,
                runtime_physical_name=config.agentcore_runtime_physical_name_audit_mcp,
            ),
        )
        self.audit_agent_throttles_alarm = self.new_alarm(
            id="AuditAgentThrottlesAlarm",
            short_name="audit-agent-throttles",
            description=(
                f"AgentCore throttled the AuditAgent runtime of {env_name}: "
                "questions are arriving faster than the account's quota allows."
            ),
            metric=self.new_runtime_metric(
                metric_name="Throttles",
                runtime_name=config.agentcore_runtime_name_audit_agent,
                runtime_physical_name=config.agentcore_runtime_physical_name_audit_agent,
            ),
        )

    def s03_create_daily_limit_alarm(self) -> None:
        """
        Create the alarm on the chat's daily limit. The web app counts a
        question with a conditional update; the update fails its condition
        exactly when the limit is reached, and DynamoDB counts those failures
        per table. The table belongs to the web invoker stack and is named
        here by its name, so neither stack depends on the other.
        """
        self.chat_daily_limit_alarm = self.new_alarm(
            id="ChatDailyLimitAlarm",
            short_name="chat-daily-limit",
            description=(
                f"The web app of {self.config.env_name} turned a question away: "
                "the day's limit of questions is reached. It takes questions "
                "again after 00:00 UTC."
            ),
            metric=cloudwatch.Metric(
                namespace="AWS/DynamoDB",
                metric_name="ConditionalCheckFailedRequests",
                dimensions_map={
                    "TableName": self.config.dynamodb_table_name_chat_daily_count,
                },
                statistic="Sum",
                period=ALARM_PERIOD,
            ),
        )
