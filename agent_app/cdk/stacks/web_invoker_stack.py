# -*- coding: utf-8 -*-

"""
The web_invoker stack: what lets the web app, hosted on Vercel, call the
``AuditAgent`` runtime without a stored AWS key.

Vercel gives every function invocation a short-lived OIDC token that says which
team, project, and environment it runs in. AWS exchanges that token for
temporary credentials of the role created here
(``sts:AssumeRoleWithWebIdentity``), and the role can do two things: invoke the
``AuditAgent`` runtime, and count a question in the table created here. On
Vercel the role's ARN (``config.iam_role_arn_web_invoker``) is the value of
``AWS_ROLE_ARN``; ``lib/agent/invoke.ts`` reads it.

Every question is a paid model call, so the web app counts the questions of a
day in a DynamoDB table and stops asking the agent when the day's limit is
reached (``lib/agent/daily-count.ts``). The limit itself is a setting of the
web app, not of this stack. On Vercel the table's ARN
(``config.dynamodb_table_arn_chat_daily_count``) is the value of
``CHAT_DAILY_TABLE_ARN``.

The stack does not depend on the runtimes' stack: the policy names the runtime
by a pattern built from its physical name, so it can be deployed before or
after them.

**One OIDC provider per issuer in an account.** IAM refuses a second provider
with the same URL, so when environments share an AWS account only one of them
creates it: the environment named by ``config.vercel_oidc_provider_env_name``.
The stacks of the others refer to that provider by its ARN. Destroying the
stack that created it leaves their roles impossible to assume.
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from constructs import Construct

from ...config.api import Config


class WebInvokerStack(cdk.Stack):
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
        self.s01_create_oidc_provider()
        self.s02_create_daily_count_table()
        self.s03_create_invoker_role()

    def s01_create_oidc_provider(self) -> None:
        """
        Make AWS trust the tokens of the Vercel team: an IAM OIDC provider for
        the team's issuer, accepting the audience Vercel puts in them. No
        thumbprint is given: IAM verifies the issuer's certificate itself.

        Only the environment the config names creates it; in any other, the
        provider is the one that environment's stack created in this account.
        """
        if self.config.env_name == self.config.vercel_oidc_provider_env_name:
            self.oidc_provider = iam.OidcProviderNative(
                self,
                "VercelOidcProvider",
                url=self.config.vercel_oidc_issuer_url,
                client_ids=[self.config.vercel_oidc_audience],
            )
        else:
            self.oidc_provider = iam.OidcProviderNative.from_oidc_provider_arn(
                self,
                "VercelOidcProvider",
                self.config.iam_oidc_provider_arn_vercel,
            )

    def s02_create_daily_count_table(self) -> None:
        """
        Create the table of the daily count: one item per UTC day (``day``,
        such as ``2026-01-31``) holding the number of questions asked that day.
        An item removes itself through ``expires_at`` some weeks later. The
        table holds nothing worth keeping, so it goes when the stack goes.
        """
        self.daily_count_table = dynamodb.Table(
            self,
            "ChatDailyCountTable",
            table_name=self.config.dynamodb_table_name_chat_daily_count,
            partition_key=dynamodb.Attribute(
                name="day",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expires_at",
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

    def s03_create_invoker_role(self) -> None:
        """
        Create the role a production deployment of the web app's Vercel project
        assumes, and nobody else: the trust policy pins both the audience and
        the subject of the token. The role may invoke the ``AuditAgent``
        runtime and update an item of the daily count, nothing more: it cannot
        read the table as a whole or delete from it.
        """
        issuer = self.config.vercel_oidc_issuer
        self.invoker_role = iam.Role(
            self,
            "WebInvokerRole",
            role_name=self.config.iam_role_name_web_invoker,
            assumed_by=iam.WebIdentityPrincipal(
                self.oidc_provider.oidc_provider_arn,
                conditions={
                    "StringEquals": {
                        f"{issuer}:aud": self.config.vercel_oidc_audience,
                        f"{issuer}:sub": self.config.vercel_oidc_subject,
                    },
                },
            ),
            inline_policies={
                "invoke-audit-agent": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["bedrock-agentcore:InvokeAgentRuntime"],
                            resources=[
                                self.config.agentcore_runtime_arn_pattern_audit_agent,
                            ],
                        ),
                    ],
                ),
                "count-chat-questions": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["dynamodb:UpdateItem"],
                            resources=[self.daily_count_table.table_arn],
                        ),
                    ],
                ),
            },
        )
