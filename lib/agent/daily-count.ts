import {
  ConditionalCheckFailedException,
  DynamoDBClient,
  UpdateItemCommand,
} from "@aws-sdk/client-dynamodb"
import { awsCredentialsProvider } from "@vercel/oidc-aws-credentials-provider"

import { dayKey, expiresAt, parseDailyLimit } from "./daily-limit"

/**
 * The daily count: how many questions the page has passed to the agent today,
 * all readers together. SERVER ONLY: it reads the environment and signs
 * requests with AWS credentials.
 *
 * `guard.ts` limits one reader; nothing there limits the total, and every
 * question is a paid model call. So a question is counted before the agent is
 * called, in one item per UTC day of a DynamoDB table, and the question that
 * would pass the limit is not counted and not asked. The update and its
 * condition are one atomic request: two questions arriving together cannot
 * both take the last place.
 *
 *   CHAT_DAILY_TABLE_ARN   the table of the `web_invoker` CDK stack:
 *                          arn:aws:dynamodb:<region>:<account>:table/<name>
 *   CHAT_DAILY_LIMIT       how many questions a day, a whole number
 *
 * On Vercel both must be set: a hosted page without its limit is a
 * misconfiguration to notice, not to run with. Elsewhere, an unset table means
 * no count; the only caller there is the developer. Setting both on a developer
 * machine counts there too, in the same table.
 *
 * The credentials are found the way `invoke.ts` finds them: the role of
 * `AWS_ROLE_ARN` on Vercel, the AWS SDK's default chain elsewhere.
 */

/** What the count says about a question. */
export type DailyCount = "allowed" | "limitReached"

/** A variable is missing or malformed: the deployment has no daily limit. */
export class DailyLimitNotConfiguredError extends Error {}

/** One client per region for the life of the server process: it caches credentials. */
const clients = new Map<string, DynamoDBClient>()

/**
 * Count one question for the day of `now`, unless the day's limit is reached.
 *
 * @throws DailyLimitNotConfiguredError when the limit is not configured. The
 *   route answers that with an error instead of calling the agent.
 * @throws whatever the AWS SDK throws when the table cannot be reached.
 */
export async function countQuestion(now: Date = new Date()): Promise<DailyCount> {
  const tableArn = process.env.CHAT_DAILY_TABLE_ARN
  if (!tableArn) {
    // Vercel sets VERCEL=1 at build time and at run time, nowhere else.
    if (process.env.VERCEL !== "1") return "allowed"
    throw new DailyLimitNotConfiguredError("Set CHAT_DAILY_TABLE_ARN (the table of the web_invoker stack).")
  }
  const limit = parseDailyLimit(process.env.CHAT_DAILY_LIMIT)
  if (limit === null) {
    throw new DailyLimitNotConfiguredError("Set CHAT_DAILY_LIMIT to a whole number of questions, at least 1.")
  }

  try {
    await clientFor(tableArn).send(
      new UpdateItemCommand({
        // DynamoDB takes a table's ARN where it takes its name.
        TableName: tableArn,
        Key: { day: { S: dayKey(now) } },
        UpdateExpression: "ADD questions :one SET expires_at = if_not_exists(expires_at, :expires)",
        ConditionExpression: "attribute_not_exists(questions) OR questions < :limit",
        ExpressionAttributeValues: {
          ":one": { N: "1" },
          ":limit": { N: String(limit) },
          ":expires": { N: String(expiresAt(now)) },
        },
      }),
    )
    return "allowed"
  } catch (error) {
    if (error instanceof ConditionalCheckFailedException) return "limitReached"
    throw error
  }
}

function clientFor(tableArn: string): DynamoDBClient {
  // arn:aws:dynamodb:<region>:<account>:table/<name>: the table's own region,
  // so the caller does not need a second variable that could disagree.
  const region = tableArn.split(":")[3]
  let client = clients.get(region)
  if (!client) {
    const roleArn = process.env.AWS_ROLE_ARN
    client = new DynamoDBClient({
      region,
      // `undefined` leaves it to the SDK's default chain.
      credentials: roleArn ? awsCredentialsProvider({ roleArn }) : undefined,
    })
    clients.set(region, client)
  }
  return client
}
