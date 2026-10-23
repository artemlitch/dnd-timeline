// card placement for the timeline, shared by index.html and the unit tests in test/
(function (root) {
  // events in date order with a day index (di) and position (idx); events sharing a day and hour are spread
  // across that hour in array order, so zooming in can always separate them
  function prepare(data) {
    const cal = data.calendar, dpm = cal.daysPerMonth, dpy = dpm * cal.monthNames.length;
    const ev = data.events.map(e => ({ ...e, di: (e.year - cal.epochYear) * dpy + (e.month - 1) * dpm + (e.day - 1) + (e.hour || 0) / 24 }))
      .sort((a, b) => a.di - b.di);
    for (let i = 0; i < ev.length;) { let j = i; while (j < ev.length && ev[j].di === ev[i].di) j++; for (let k = i; k < j; k++) ev[k].di += (k - i) / (j - i) / 24; i = j; }
    ev.forEach((e, i) => { e.idx = i; });
    return ev;
  }

  // for each event, the narrowest span in days covering it and `rows` higher-ranked events (major first, then every
  // 2nd, 4th, 8th event so they spread evenly). Higher-ranked events count whether they show or not, so the span is
  // fixed and the event shows at every zoom that stretches it to a card width
  function spans(events, rows) {
    const score = e => { let n = e.idx + 1, r = 0; while (!(n & 1)) { n >>= 1; r++; } return (e.major ? 64 : 0) + r; };
    const higher = [], out = new Map();
    for (const e of [...events].sort((a, b) => score(b) - score(a) || a.idx - b.idx)) {
      let p = 0, q = higher.length; while (p < q) { const m = (p + q) >> 1; if (higher[m] < e.di) p = m + 1; else q = m; }
      let s = Infinity;
      for (let k = 0; k <= rows; k++) {
        const l = p - k, r = p + rows - k - 1;
        if (l < 0 || (rows - k > 0 && r >= higher.length)) continue;
        s = Math.min(s, (rows - k > 0 ? higher[r] : e.di) - (k > 0 ? higher[l] : e.di));
      }
      out.set(e.id, s); higher.splice(p, 0, e.di);
    }
    return out;
  }

  // shown events take rows in date order, each the highest row whose last card it clears; a card width never holds
  // more than `rows` shown events, so one always fits. Returns id -> row; `need` is a card width in days
  function place(events, rows, need, span = spans(events, rows)) {
    const last = new Array(rows), placed = new Map();
    for (const e of events) {
      if (span.get(e.id) < need) continue;
      for (let r = 0; r < rows; r++) { if (last[r] === undefined || e.di - last[r] >= need) { last[r] = e.di; placed.set(e.id, r); break; } }
    }
    return placed;
  }

  const api = { prepare, spans, place };
  if (typeof module === 'object' && module.exports) module.exports = api; else root.Placement = api;
})(this);
