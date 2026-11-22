import { test } from 'node:test';
import assert from 'node:assert';

import {
  AgentResponseError,
  MAX_PROMPT_CHARS,
  humanizeCategory,
  lastUserText,
  parseAgentResponse,
  toRuntimeSessionId,
} from '../lib/agent/contract.ts';

// A fictional domain: none of these IDs exists in the audit dataset.
const VERDICT = {
  session_id: 'ses_widget_001',
  risky: true,
  severity: 'high',
  categories: ['WIDGET_MISUSE'],
  policy_ids: ['W-01'],
  flagged_call_ids: ['call_2'],
  rationale: 'call_2 shipped 900 widgets without an approval.',
};

const user = (text) => ({ role: 'user', parts: [{ type: 'text', text }] });
const assistant = (text) => ({ role: 'assistant', parts: [{ type: 'text', text }] });

test('lastUserText takes the last user message, trimmed, text parts only', () => {
  const messages = [user('first'), assistant('answer'), user('  second  ')];
  assert.strictEqual(lastUserText(messages), 'second');
  // an assistant message after it does not hide it
  assert.strictEqual(lastUserText([user('a'), assistant('b')]), 'a');
  // several text parts are one question; other parts are not text
  const mixed = {
    role: 'user',
    parts: [{ type: 'text', text: 'one' }, { type: 'file', url: 'x' }, { type: 'text', text: 'two' }],
  };
  assert.strictEqual(lastUserText([mixed]), 'one\ntwo');
});

test('lastUserText is empty for anything that is not a chat with a user message', () => {
  for (const messages of [undefined, null, 'hi', {}, [], [assistant('a')], [{ role: 'user' }], [null, 3]]) {
    assert.strictEqual(lastUserText(messages), '');
  }
  assert.strictEqual(lastUserText([{ role: 'user', parts: [{ type: 'text', text: 7 }] }]), '');
});

test('toRuntimeSessionId maps a chat to one session AgentCore accepts', () => {
  const random = () => 'random-id';
  const id = toRuntimeSessionId('AbCdEfGhIjKlMnOp', random);
  assert.strictEqual(id, 'agent-audit-chat-AbCdEfGhIjKlMnOp');
  assert.strictEqual(id.length, 33); // the minimum AgentCore accepts
  // the same chat, the same session
  assert.strictEqual(toRuntimeSessionId('AbCdEfGhIjKlMnOp', random), id);
  // a short ID is padded, a long one cut, and both stay well formed
  assert.strictEqual(toRuntimeSessionId('abc', random).length, 33);
  assert.strictEqual(toRuntimeSessionId('x'.repeat(500), random).length, 256);
  // characters AgentCore refuses are dropped
  assert.strictEqual(toRuntimeSessionId('a b/c?d', random), 'agent-audit-chat-abcd000000000000');
  // no usable chat ID: a conversation of its own
  for (const chatId of [undefined, 42, '', '///']) {
    assert.strictEqual(toRuntimeSessionId(chatId, random), 'agent-audit-chat-random-id0000000');
  }
});

test('parseAgentResponse accepts the agent contract', () => {
  const clean = { ...VERDICT, risky: false, severity: 'none', categories: [], policy_ids: [], flagged_call_ids: [] };
  const answer = parseAgentResponse({ result: 'ok', verdicts: [VERDICT, clean], refused: false });
  assert.deepStrictEqual(answer, { result: 'ok', verdicts: [VERDICT, clean], refused: false });
  // a refusal carries no verdict
  assert.deepStrictEqual(parseAgentResponse({ result: 'declined', verdicts: [], refused: true }), {
    result: 'declined',
    verdicts: [],
    refused: true,
  });
  // a runtime from before `refused` existed never refused
  assert.strictEqual(parseAgentResponse({ result: 'ok', verdicts: [] }).refused, false);
  // fields this page does not know are dropped, not passed on
  const extra = parseAgentResponse({ result: 'ok', verdicts: [{ ...VERDICT, note: 'x' }], model: 'm' });
  assert.deepStrictEqual(extra.verdicts, [VERDICT]);
  assert.ok(!('model' in extra));
});

test('parseAgentResponse names the field that is wrong', () => {
  const cases = [
    [null, 'the answer is not an object'],
    [[], 'the answer is not an object'],
    [{ error: 'boom' }, 'result is not a string'],
    [{ result: 'ok' }, 'verdicts is not a list'],
    [{ result: 'ok', verdicts: [], refused: 'no' }, 'refused is not a boolean'],
    [{ result: 'ok', verdicts: ['x'] }, 'verdicts[0] is not an object'],
    [{ result: 'ok', verdicts: [{ ...VERDICT, session_id: 1 }] }, 'verdicts[0].session_id is not a string'],
    [{ result: 'ok', verdicts: [{ ...VERDICT, risky: 'yes' }] }, 'verdicts[0].risky is not a boolean'],
    [{ result: 'ok', verdicts: [{ ...VERDICT, severity: 'severe' }] }, 'verdicts[0].severity is not a severity'],
    [{ result: 'ok', verdicts: [{ ...VERDICT, rationale: null }] }, 'verdicts[0].rationale is not a string'],
    [{ result: 'ok', verdicts: [VERDICT, { ...VERDICT, policy_ids: 'W-01' }] }, 'verdicts[1].policy_ids is not a list of strings'],
    [{ result: 'ok', verdicts: [{ ...VERDICT, categories: [1] }] }, 'verdicts[0].categories is not a list of strings'],
    [{ result: 'ok', verdicts: [{ ...VERDICT, flagged_call_ids: undefined }] }, 'verdicts[0].flagged_call_ids is not a list of strings'],
  ];
  for (const [raw, message] of cases) {
    assert.throws(() => parseAgentResponse(raw), (error) => {
      assert.ok(error instanceof AgentResponseError);
      assert.strictEqual(error.message, message);
      return true;
    });
  }
});

test('humanizeCategory and the prompt limit', () => {
  assert.strictEqual(humanizeCategory('WIDGET_MISUSE'), 'Widget misuse');
  assert.strictEqual(humanizeCategory('critical'), 'Critical');
  // An acronym keeps its capitals, wherever it stands.
  assert.strictEqual(humanizeCategory('PII_WIDGET'), 'PII widget');
  assert.strictEqual(humanizeCategory('WIDGET_SSRF_ACCESS'), 'Widget SSRF access');
  assert.strictEqual(humanizeCategory(''), '');
  assert.strictEqual(MAX_PROMPT_CHARS, 4000);
});
