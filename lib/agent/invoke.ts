import { BedrockAgentCoreClient, InvokeAgentRuntimeCommand } from "@aws-sdk/client-bedrock-agentcore"
import { awsCredentialsProvider } from "@vercel/oidc-aws-credentials-provider"

import { type AuditAgentResponse, parseAgentResponse } from "./contract"

/**
 * Calling the `AuditAgent` runtime. SERVER ONLY: it reads the environment and
 * signs requests with AWS credentials.
 *
 * Two ways to reach the agent, chosen by the environment:
 *
 *   AGENTCORE_RUNTIME_AUDITAGENT_ARN   the deployed runtime, through
 *                                      `InvokeAgentRuntime`. The variable has the
 *                                      name `bind()` gives a runtime's ARN on the
 *                                      Python side.
 *   AGENT_URL                          a runtime on this machine (`mise run
 *                                      ac-local-audit-agent`, port 18734), over
 *                                      plain HTTP. No AWS involved. The same
 *                                      variable `agent_app/devtools/agent_client.py`
 *                                      reads.
 *
 * `AGENT_URL` wins when both are set: it is only ever set by someone who is
 * running the agent locally and wants the page to use it.
 *
 * The call to the deployed runtime is signed with AWS credentials, found in one
 * of two ways:
 *
 *   AWS_ROLE_ARN set     on Vercel. The function has no AWS key: it shows AWS the
 *                        OIDC token Vercel gives every invocation, and gets
 *                        temporary credentials of this role in exchange. The role
 *                        is the one of the `web_invoker` CDK stack, which can
 *                        invoke the runtime and do nothing else.
 *   AWS_ROLE_ARN unset   on a developer machine: the AWS SDK's default chain
 *                        (`AWS_PROFILE`, else the profile named "default").
 */

/** The header AgentCore Runtime sets from `runtimeSessionId`; a local server reads it the same way. */
const SESSION_ID_HEADER = "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"

/** Neither variable is set: the deployment is missing its configuration. */
export class AgentNotConfiguredError extends Error {}

/** One client per region for the life of the server process: it caches credentials. */
const clients = new Map<string, BedrockAgentCoreClient>()

/**
 * Ask the agent `prompt` in the conversation `runtimeSessionId`, and return its
 * validated answer. An audit takes several model calls, so this takes from a
 * few seconds to a minute.
 *
 * @throws AgentNotConfiguredError when no way to reach the agent is configured.
 * @throws AgentResponseError when the agent's answer has the wrong shape.
 * @throws whatever the AWS SDK or `fetch` throws when the call itself fails.
 */
export async function invokeAuditAgent(
  prompt: string,
  runtimeSessionId: string,
): Promise<AuditAgentResponse> {
  const localUrl = process.env.AGENT_URL
  if (localUrl) return parseAgentResponse(await invokeLocal(localUrl, prompt, runtimeSessionId))

  const arn = process.env.AGENTCORE_RUNTIME_AUDITAGENT_ARN
  if (arn) return parseAgentResponse(await invokeDeployed(arn, prompt, runtimeSessionId))

  throw new AgentNotConfiguredError(
    "Set AGENTCORE_RUNTIME_AUDITAGENT_ARN (the deployed runtime) or AGENT_URL (a local one).",
  )
}

async function invokeLocal(url: string, prompt: string, runtimeSessionId: string): Promise<unknown> {
  const response = await fetch(`${url.replace(/\/+$/, "")}/invocations`, {
    method: "POST",
    headers: { "Content-Type": "application/json", [SESSION_ID_HEADER]: runtimeSessionId },
    body: JSON.stringify({ prompt }),
  })
  if (!response.ok) {
    throw new Error(`the local agent answered ${response.status}: ${await response.text()}`)
  }
  return response.json()
}

async function invokeDeployed(arn: string, prompt: string, runtimeSessionId: string): Promise<unknown> {
  // arn:aws:bedrock-agentcore:<region>:<account>:runtime/<id>: the runtime's own
  // region, so the caller does not need a second variable that could disagree.
  const region = arn.split(":")[3]
  let client = clients.get(region)
  if (!client) {
    const roleArn = process.env.AWS_ROLE_ARN
    client = new BedrockAgentCoreClient({
      region,
      // `undefined` leaves it to the SDK's default chain.
      credentials: roleArn ? awsCredentialsProvider({ roleArn }) : undefined,
    })
    clients.set(region, client)
  }
  const output = await client.send(
    new InvokeAgentRuntimeCommand({
      agentRuntimeArn: arn,
      runtimeSessionId,
      contentType: "application/json",
      accept: "application/json",
      payload: new TextEncoder().encode(JSON.stringify({ prompt })),
    }),
  )
  if (!output.response) throw new Error("the runtime answered without a body")
  return JSON.parse(await output.response.transformToString())
}
