const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..');
const read = p => fs.readFileSync(path.join(ROOT, p), 'utf8');
const json = p => JSON.parse(read(p));

const dir = path.join(ROOT, 'gen/prompts');
const prompts = fs.readdirSync(dir).filter(f => f.endsWith('.prompt.txt'))
  .map(f => ({ id: f.replace('.prompt.txt', ''), text: fs.readFileSync(path.join(dir, f), 'utf8') }));

const framings = new Set(Object.keys(json('gen/world/framing.json')));
const settings = new Map(json('gen/world/settings.json').map(s => [s.id, new Set((s.sublocations || []).map(x => x.id))]));
const castNames = new Set([...Object.keys(json('gen/world/cast.json')), ...Object.keys(json('gen/world/ships.json'))]);
const mapPages = new Map(json('gen/refs/roll20/maps/index.json').map(p => [p.page.trim(), p.maps.length]));

const offenders = (check) => prompts.flatMap(p => { const problem = check(p); return problem ? [`${p.id}: ${problem}`] : []; });
const expectNone = (list) => assert.deepEqual(list, [], `\n${list.join('\n')}`);

test('there are prompts to check', () => {
  assert.ok(prompts.length > 0);
});

test('every prompt has its sections in order', () => {
  const order = ['{tone}', 'This scene is', 'FRAMING', 'SETTING', 'THE MOMENT', 'CAST', 'REFERENCES', '{references}'];
  expectNone(offenders(({ text }) => {
    let at = -1;
    for (const part of order) {
      const i = text.indexOf(part, at + 1);
      if (i === -1) return `missing or out of order: ${part}`;
      at = i;
    }
    return null;
  }));
});

test('every prompt uses a framing from framing.json', () => {
  expectNone(offenders(({ text }) => {
    const m = text.match(/\{framing:(\w+)\}/);
    return !m ? 'no {framing:...}' : framings.has(m[1]) ? null : `unknown framing "${m[1]}"`;
  }));
});

test('every prompt names a setting and place that exist in settings.json', () => {
  expectNone(offenders(({ text }) => {
    const m = text.match(/\{setting:([^/}]+)(?:\/([^}]+))?\}/);
    if (!m) return 'no {setting:...}';
    if (!settings.has(m[1])) return `unknown setting "${m[1]}"`;
    return m[2] && !settings.get(m[1]).has(m[2]) ? `unknown place "${m[2]}" in ${m[1]}` : null;
  }));
});

test('every prompt has a map', () => {
  expectNone(offenders(({ text }) => (/\{maps:[^}]+\}/.test(text) ? null : 'no {maps:...}')));
});

test('every map is a Roll20 page that exists, and #n points at an image on it', () => {
  expectNone(offenders(({ text }) => {
    const m = text.match(/\{maps:([^}]+)\}/);
    if (!m) return null;
    for (const item of m[1].split('|')) {
      const [name, n] = item.trim().split('#');
      if (!mapPages.has(name)) return `unknown map page "${name}"`;
      if (n && !(Number(n) >= 1 && Number(n) <= mapPages.get(name))) return `"${name}" has no image #${n}`;
    }
    return null;
  }));
});

test('every {cast:Name} is in cast.json or ships.json', () => {
  expectNone(offenders(({ text }) => {
    const unknown = [...text.matchAll(/\{cast:([^}]+)\}/g)].map(m => m[1].trim()).filter(n => !castNames.has(n));
    return unknown.length ? `unknown cast ${unknown.join(', ')}` : null;
  }));
});

test('every placeholder is one image.py fills', () => {
  expectNone(offenders(({ text }) => {
    const bad = [...text.matchAll(/\{([^}]*)\}/g)].map(m => m[0])
      .filter(t => !/^\{(tone|references|(framing|setting|maps|cast):[^}]+)\}$/.test(t));
    return bad.length ? `unknown placeholder ${bad.join(', ')}` : null;
  }));
});
