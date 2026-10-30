const test = require('node:test');
const assert = require('node:assert/strict');
const { prepare, place, nearestShown, stepShown, clusterZoom, dateLabel, maxZoom, matches, cardLook, ROWS } = require('../site/placement.js');

const timeline = require('../site/timeline.json');
const events = prepare(timeline);

test('the timeline uses at most two rows of cards', () => {
  assert.equal(ROWS, 2);
});
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

test('a shown card never moves to a lower row when zooming in', () => {
  let prev = shownAt(zooms[0]);
  for (const p of zooms.slice(1)) {
    const cur = shownAt(p);
    for (const [id, r] of prev) if (cur.has(id)) assert.ok(cur.get(id) <= r, `${id} drops from row ${r} to row ${cur.get(id)} when zooming in to ${p.toFixed(3)} px/day`);
    prev = cur;
  }
});

test('a card sits below the top row only when every row above it is taken nearby', () => {
  // the layout is stepped in 2% zoom increments, so "nearby" allows one step of slack
  for (const p of zooms) {
    const shown = shownAt(p), need = (CARD / p) * 1.02, byRow = Array.from({ length: ROWS }, () => []);
    const di = new Map(events.map(e => [e.id, e.di]));
    for (const [id, r] of shown) byRow[r].push(di.get(id));
    for (const [id, r] of shown) for (let up = 0; up < r; up++)
      assert.ok(byRow[up].some(d => Math.abs(d - di.get(id)) < need), `${id} sits in row ${r} at ${p.toFixed(3)} px/day though row ${up} has room`);
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

test('the tile nearest a day is the closest full-size card, not a closer faded one', () => {
  const p = 0.5, shown = shownAt(p);
  const faded = events.find(e => !shown.has(e.id));
  const picked = nearestShown(events, shown, faded.di);
  assert.ok(shown.has(picked.id));
  const best = Math.min(...events.filter(e => shown.has(e.id)).map(e => Math.abs(e.di - faded.di)));
  assert.equal(Math.abs(picked.di - faded.di), best);
});

test('with no full-size cards there is no nearest tile', () => {
  assert.equal(nearestShown(events, new Map(), events[0].di), null);
});

test('stepping moves to the next full-size card in date order, skipping faded ones', () => {
  const shown = shownAt(0.5), list = events.filter(e => shown.has(e.id));
  const from = list[3], next = stepShown(events, shown, from, 1), prev = stepShown(events, shown, from, -1);
  assert.equal(next.id, list[4].id);
  assert.equal(prev.id, list[2].id);
});

test('stepping from a faded event goes to the nearest full-size card in that direction', () => {
  const shown = shownAt(0.5);
  const faded = events.find(e => !shown.has(e.id) && events.some(f => f.di > e.di && shown.has(f.id)));
  const next = stepShown(events, shown, faded, 1);
  assert.equal(next.id, events.find(f => f.di > faded.di && shown.has(f.id)).id);
});

test('clicking a bubble whose run is wider than the screen zooms in on it, never out', () => {
  const { p, center } = clusterZoom(100, 2100, 1, 1200, 5000);
  assert.ok(p >= 2, `zoom went from 1 to ${p} px/day`);
  assert.equal(center, 1100);
});

test('clicking a bubble whose run fits on screen zooms in to fit it', () => {
  const { p, center } = clusterZoom(100, 102, 1, 1200, 5000);
  assert.equal(p, (1200 - 300) / 2);
  assert.equal(center, 101);
});

test('clicking a bubble at the closest zoom keeps the zoom', () => {
  assert.equal(clusterZoom(100, 2100, 5000, 1200, 5000).p, 5000);
});

test('stepping past the last full-size card gives nothing', () => {
  const shown = shownAt(0.5), list = events.filter(e => shown.has(e.id));
  assert.equal(stepShown(events, shown, list[list.length - 1], 1), null);
});

test('an event with a known day and hour shows them', () => {
  assert.equal(dateLabel({ year: 993, month: 1, day: 18, hour: 8 }, timeline.calendar), 'Wir, Zarantyr 18, 993 YK, 08:00');
});

test('an event known only to the year says around that year', () => {
  assert.equal(dateLabel({ year: 953, month: 1, day: 1, hour: 12, around: 'year' }, timeline.calendar), 'Around 953 YK');
});

test('an event known only to the month says around that month', () => {
  assert.equal(dateLabel({ year: 992, month: 12, day: 1, hour: 12, around: 'month' }, timeline.calendar), 'Around Vult, 992 YK');
});

test('at the maximum zoom every event shows as a full card', () => {
  const zmax = maxZoom(events, CARD);
  assert.equal(shownAt(zmax).size, events.length);
});

test('a faded card is only dimmed, and can still be clicked open', () => {
  const html = require('node:fs').readFileSync(require('node:path').join(__dirname, '../site/index.html'), 'utf8');
  const ghost = [...html.matchAll(/\.card\.ghost[^{]*\{[^}]*\}/g)].map(m => m[0]).join(' ');
  assert.doesNotMatch(ghost, /pointer-events:\s*none/);
  assert.doesNotMatch(ghost, /opacity:\s*\.2\b/);
});

test('a search never hides an event: one that does not match is drawn dimmed', () => {
  const e = { id: 'x', title: 'Saxophone Solo', kind: 'social' };
  assert.equal(cardLook(e, new Map(), 'kingsblade'), 'dimmed');
});

test('a search match with room shows as a full card', () => {
  const e = { id: 'x', title: 'Tour of the Kingsblade', kind: 'travel' };
  assert.equal(cardLook(e, new Map([['x', 0]]), 'kingsblade'), 'full');
});

test('a search match with no room shows as a faded card', () => {
  const e = { id: 'x', title: 'Tour of the Kingsblade', kind: 'travel' };
  assert.equal(cardLook(e, new Map(), 'kingsblade'), 'faded');
});

test('a search matches tags, the description and the session', () => {
  const e = { id: 'x', title: 'Dinner', tags: ['Lirael'], detail: 'the spoon flies', session: 12, kind: 'social' };
  for (const q of ['lirael', 'spoon', 'session 12', 's12']) assert.ok(matches(e, q), q);
  assert.ok(!matches(e, 'kingsblade'));
});

test('with no search every event matches', () => {
  assert.ok(matches({ id: 'x', title: 'Dinner' }, ''));
});
