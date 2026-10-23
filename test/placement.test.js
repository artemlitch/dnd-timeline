const test = require('node:test');
const assert = require('node:assert/strict');
const { prepare, place } = require('../site/placement.js');

const timeline = require('../site/timeline.json');
const events = prepare(timeline);
const ROWS = 3;
const CARD = 255;

// zoom levels in px per day, from a whole century on screen to a few minutes per card
const zooms = [];
for (let p = 0.02; p < 50000; p *= 1.07) zooms.push(p);

const shownAt = (p, list = events) => place(list, ROWS, CARD / p);

test('a card shown at one zoom stays shown at every closer zoom', () => {
  let prev = shownAt(zooms[0]);
  for (const p of zooms.slice(1)) {
    const cur = shownAt(p);
    for (const id of prev.keys()) assert.ok(cur.has(id), `${id} hides when zooming in to ${p.toFixed(3)} px/day`);
    prev = cur;
  }
});

test('two cards in the same row never overlap', () => {
  for (const p of zooms) {
    const need = CARD / p, last = new Map(), shown = shownAt(p);
    for (const e of events) {
      const r = shown.get(e.id);
      if (r === undefined) continue;
      if (last.has(r)) assert.ok(e.di - last.get(r) >= need, `${e.id} overlaps the card before it in row ${r} at ${p.toFixed(3)} px/day`);
      last.set(r, e.di);
    }
  }
});

test('every row number is below the row count', () => {
  for (const p of zooms) for (const r of shownAt(p).values()) assert.ok(r >= 0 && r < ROWS);
});

test('everything shows once the zoom spreads every event a card apart', () => {
  assert.equal(shownAt(zooms[zooms.length - 1]).size, events.length);
});
