# -*- coding: utf-8 -*-

"""
The web_invoker stack: what lets the web app, hosted on Vercel, call the
``AuditAgent`` runtime without a stored AWS key.

Vercel gives every function invocation a short-lived OIDC token that says which
team, project, and environment it runs in. AWS exchanges that token for
temporary credentials of the role created here
(``sts:AssumeRoleWithWebIdentity``), and the role can do one thing: invoke the
``AuditAgent`` runtime. On Vercel the role's ARN
(``config.iam_role_arn_web_invoker``) is the value of ``AWS_ROLE_ARN``;
``lib/agent/invoke.ts`` reads it.

The stack does not depend on the runtimes' stack: the policy names the runtime
by a pattern built from its physical name, so it can be deployed before or
after them.

**One OIDC provider per issuer in an account.** IAM refuses a second provider
with the same URL, so two environments that share an AWS account cannot both
deploy this stack as it is: the second one would have to import the provider
instead of creating it.
"""

from __future__ import annotations

import aws_cdk as cdk
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
        self.s02_create_invoker_role()

    def s01_create_oidc_provider(self) -> None:
        """
        Make AWS trust the tokens of the Vercel team: an IAM OIDC provider for
        the team's issuer, accepting the audience Vercel puts in them. No
        thumbprint is given: IAM verifies the issuer's certificate itself.
        """
        self.oidc_provider = iam.OidcProviderNative(
            self,
            "VercelOidcProvider",
            url=self.config.vercel_oidc_issuer_url,
            client_ids=[self.config.vercel_oidc_audience],
        )

    def s02_create_invoker_role(self) -> None:
        """
        Create the role a production deployment of the web app's Vercel project
        assumes, and nobody else: the trust policy pins both the audience and
        the subject of the token. The role may invoke the ``AuditAgent``
        runtime and nothing more; the model's cost per invocation is limited
        by the web app, not here.
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
            },
        )
