import { test } from 'node:test';
import assert from 'node:assert';

import {
  COUNT_KEPT_DAYS,
  dayKey,
  expiresAt,
  parseDailyLimit,
} from '../lib/agent/daily-limit.ts';

test('parseDailyLimit takes a whole number of at least 1', () => {
  assert.strictEqual(parseDailyLimit('50'), 50);
  assert.strictEqual(parseDailyLimit(' 7 '), 7);
  assert.strictEqual(parseDailyLimit('1'), 1);
});

test('parseDailyLimit reads anything else as a missing setting', () => {
  // never "no limit": zero, a sign, a fraction, words, nothing at all
  for (const value of [undefined, '', ' ', '0', '-5', '+5', '2.5', '1e3', '050', 'fifty', '50 a day']) {
    assert.strictEqual(parseDailyLimit(value), null, String(value));
  }
});

test('dayKey is the UTC date, whatever the time of day', () => {
  assert.strictEqual(dayKey(new Date('2026-01-31T00:00:00Z')), '2026-01-31');
  assert.strictEqual(dayKey(new Date('2026-01-31T23:59:59.999Z')), '2026-01-31');
  assert.strictEqual(dayKey(new Date('2026-02-01T00:00:00Z')), '2026-02-01');
  // 23:30 on the 31st in New York is already the 1st in UTC
  assert.strictEqual(dayKey(new Date('2026-01-31T23:30:00-05:00')), '2026-02-01');
});

test('expiresAt is the same for every moment of a day, a fixed number of days after it began', () => {
  const dayStart = Date.UTC(2026, 0, 31) / 1000;
  const expected = dayStart + COUNT_KEPT_DAYS * 86400;
  assert.strictEqual(expiresAt(new Date('2026-01-31T00:00:00Z')), expected);
  assert.strictEqual(expiresAt(new Date('2026-01-31T23:59:59.999Z')), expected);
  assert.strictEqual(expiresAt(new Date('2026-02-01T00:00:00Z')), expected + 86400);
});
