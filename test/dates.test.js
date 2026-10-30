const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..');
const json = p => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));
const data = json('site/timeline.json');
const moments = json('site/timeline-list/timeline.json');
const events = new Map(data.events.map(e => [e.id, e]));

test('every event sits on the date of its moment in the true timeline', () => {
  const wrong = [];
  for (const m of moments) {
    for (const { event } of m.images) {
      const e = events.get(event);
      const off = ['year', 'month', 'day'].filter(k => m.date[k] != null && e[k] !== m.date[k]);
      if (off.length) wrong.push(`${event}: ${e.year}/${e.month}/${e.day}, the true timeline says ${m.doc_date}`);
    }
  }
  assert.deepEqual(wrong, [], `\n${wrong.join('\n')}`);
});

const momentOf = new Map(moments.flatMap(m => m.images.map(i => [i.event, m])));

test('an event the true timeline gives no exact day for says around', () => {
  const wrong = [];
  for (const m of moments) {
    const want = m.date.day ? undefined : m.date.month ? 'month' : 'year';
    for (const { event } of m.images) if (events.get(event).around !== want) wrong.push(`${event}: around=${events.get(event).around}, the true timeline says ${m.doc_date}`);
  }
  assert.deepEqual(wrong, [], `\n${wrong.join('\n')}`);
});

test('every around event belongs to a moment of the true timeline', () => {
  assert.deepEqual(data.events.filter(e => e.around && !momentOf.has(e.id)).map(e => e.id), []);
});

// around a year: a month apart either side of mid-year; around a month: a week apart either side of mid-month
test('around events in the same year or month are spread out in true timeline order', () => {
  const groups = new Map();
  for (const e of data.events.filter(e => e.around && momentOf.has(e.id))) {
    const k = e.around === 'year' ? `${e.year}` : `${e.year}/${e.month}`;
    groups.set(k, [...(groups.get(k) || []), e]);
  }
  const wrong = [];
  for (const list of groups.values()) {
    list.sort((a, b) => momentOf.get(a.id).n - momentOf.get(b.id).n);
    const first = list[0].around === 'year' ? 7 - Math.floor(list.length / 2) : 15 - 7 * Math.floor(list.length / 2);
    list.forEach((e, i) => {
      const [month, day] = e.around === 'year' ? [first + i, 1] : [e.month, first + 7 * i];
      if (e.month !== month || e.day !== day) wrong.push(`${e.id}: ${e.year}/${e.month}/${e.day}, want ${e.year}/${month}/${day}`);
    });
  }
  assert.deepEqual(wrong, [], `\n${wrong.join('\n')}`);
});

test('within a campaign day, events follow the order of the true timeline', () => {
  const at = e => ((e.year * 12 + e.month) * 28 + e.day) * 24 + (e.hour || 0);
  const wrong = [];
  const order = data.events.map(e => e.id);
  for (const m of moments.filter(m => m.date.day)) {
    const ids = m.images.map(i => i.event);
    for (let i = 1; i < ids.length; i++) {
      const a = events.get(ids[i - 1]), b = events.get(ids[i]);
      if (at(a) > at(b) || (at(a) === at(b) && order.indexOf(a.id) > order.indexOf(b.id))) wrong.push(`${a.id} comes after ${b.id}`);
    }
  }
  assert.deepEqual(wrong, [], `\n${wrong.join('\n')}`);
});

test('no event falls before the calendar starts, where the page cannot draw it', () => {
  const early = data.events.filter(e => e.year < data.calendar.epochYear).map(e => `${e.id} (${e.year})`);
  assert.deepEqual(early, []);
});

test('the act and arc bands cover their sessions', () => {
  const day = d => (d.year * 12 + d.month - 1) * 28 + d.day;
  const wrong = [];
  for (const era of data.eras.filter(r => r.id.startsWith('act-') || r.id.startsWith('arc-'))) {
    const inEra = data.events.filter(e => e.session && (era.id.startsWith('act-') ? `act-${e.act}` === era.id : e.arc === era.title));
    for (const e of inEra) if (day(e) < day(era.start) || day(e) > day(era.end)) wrong.push(`${e.id} (${e.day}) is outside ${era.title}`);
  }
  assert.deepEqual(wrong, [], `\n${wrong.join('\n')}`);
});
