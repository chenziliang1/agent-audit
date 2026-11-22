import { test } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

import { parse } from 'smol-toml';

import {
  KICKSTART_COUNT,
  KICKSTARTS_PER_KIND,
  checkSuggestedActions,
  renderKindOf,
} from '../lib/site/kickstarts.ts';

const ROOT = path.join(import.meta.dirname, '..');

// A fictional domain: none of these questions is in data/site.toml.
const WORDING = {
  verdict: 'Audit session ses_widget_001. Did it ship too many widgets?',
  table: 'List the widget lines. Show it as a Markdown table.',
  flowchart: 'Draw how a widget is packed as a Mermaid flowchart.',
  free: 'What is a widget?',
};

/** A valid set: `KICKSTARTS_PER_KIND` questions of each kind. */
function validActions() {
  const actions = [];
  for (const [render, action] of Object.entries(WORDING)) {
    for (let i = 1; i <= KICKSTARTS_PER_KIND; i++) {
      actions.push({ render, title: `${render} ${i}`, label: 'A widget question', action });
    }
  }
  return actions;
}

test('renderKindOf reads the kind from the wording', () => {
  for (const [render, action] of Object.entries(WORDING)) {
    assert.strictEqual(renderKindOf(action), render);
  }
  // A flowchart of a session audits it too; the flowchart wins.
  assert.strictEqual(
    renderKindOf('Audit session ses_widget_001, then draw it as a Mermaid flowchart.'),
    'flowchart',
  );
});

test('checkSuggestedActions accepts a full, consistent set', () => {
  const actions = validActions();
  assert.strictEqual(actions.length, KICKSTART_COUNT);
  assert.deepStrictEqual(checkSuggestedActions(actions), []);
});

test('checkSuggestedActions names what is wrong', () => {
  const short = validActions().slice(1);
  assert.ok(checkSuggestedActions(short).some((p) => p.includes(`not ${KICKSTART_COUNT}`)));

  // Marked as a table, worded as prose: the glyph would promise a table nobody asked for.
  const mismatch = validActions();
  mismatch[0] = { ...mismatch[0], render: 'table' };
  const problems = checkSuggestedActions(mismatch);
  assert.ok(problems.some((p) => p.includes('is marked "table" but its wording produces "verdict"')));
  assert.ok(problems.some((p) => p.includes('questions are marked "verdict"')));

  const unknown = validActions();
  unknown[0] = { ...unknown[0], render: 'chart' };
  assert.ok(checkSuggestedActions(unknown).some((p) => p.includes('unknown render "chart"')));

  const both = validActions();
  both[0] = { ...both[0], action: `${WORDING.table} ${WORDING.flowchart}` };
  assert.ok(checkSuggestedActions(both).some((p) => p.includes('both a table and a flowchart')));
});

// The two tests below read the real files: they are what fails when the copy
// and the bundled dataset drift apart.

test('data/site.toml keeps the rules of the kickstart questions', () => {
  const site = parse(fs.readFileSync(path.join(ROOT, 'data', 'site.toml'), 'utf-8'));
  assert.deepStrictEqual(checkSuggestedActions(site.chat.suggestedActions), []);
});

test('every session ID in data/site.toml exists in the bundled traces', () => {
  const toml = fs.readFileSync(path.join(ROOT, 'data', 'site.toml'), 'utf-8');
  const named = new Set(toml.match(/ses_[0-9a-f]{12}/g));
  assert.ok(named.size > 0);

  const traces = zlib
    .gunzipSync(fs.readFileSync(path.join(ROOT, 'agent_app', 'audit', 'data', 'traces.jsonl.gz')))
    .toString('utf-8');
  const recorded = new Set(
    traces
      .split('\n')
      .filter((line) => line.trim() !== '')
      .map((line) => JSON.parse(line).session_id),
  );
  const missing = [...named].filter((id) => !recorded.has(id));
  assert.deepStrictEqual(missing, []);
});

test('every agent ID in data/site.toml exists in the bundled agents', () => {
  const toml = fs.readFileSync(path.join(ROOT, 'data', 'site.toml'), 'utf-8');
  const named = new Set(toml.match(/agt_[0-9a-f]{12}/g));
  assert.ok(named.size > 0);

  const recorded = new Set(
    fs
      .readFileSync(path.join(ROOT, 'agent_app', 'audit', 'data', 'agents.jsonl'), 'utf-8')
      .split('\n')
      .filter((line) => line.trim() !== '')
      .map((line) => JSON.parse(line).agent_id),
  );
  const missing = [...named].filter((id) => !recorded.has(id));
  assert.deepStrictEqual(missing, []);
});
