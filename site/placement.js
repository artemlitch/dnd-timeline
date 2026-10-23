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

  // the layout at a zoom is what you get zooming in to it from all the way out, in small steps of card width (in
  // days). At each step shown cards move up to the highest row that has room, then hidden cards take the highest
  // free row, both in rank order (major first, then every 2nd, 4th, 8th event so they spread evenly). Zooming in only
  // pulls cards apart, so a shown card never hides and never moves down
  const NEED0 = 1e5, STEP = 1.02;
  const sims = new WeakMap();
  function simulation(events, rows) {
    let byRows = sims.get(events);
    if (!byRows) sims.set(events, byRows = new Map());
    let sim = byRows.get(rows);
    if (sim) return sim;
    const score = e => { let n = e.idx + 1, r = 0; while (!(n & 1)) { n >>= 1; r++; } return (e.major ? 64 : 0) + r; };
    const order = [...events].sort((a, b) => score(b) - score(a) || a.idx - b.idx);
    sim = { order, rowDi: Array.from({ length: rows }, () => []), row: new Map(), layouts: [] };
    byRows.set(rows, sim);
    return sim;
  }
  const lowerBound = (a, x) => { let p = 0, q = a.length; while (p < q) { const m = (p + q) >> 1; if (a[m] < x) p = m + 1; else q = m; } return p; };
  function step(sim, need) {
    const free = (r, di) => { const a = sim.rowDi[r], p = lowerBound(a, di); return (p === a.length || a[p] - di >= need) && (p === 0 || di - a[p - 1] >= need); };
    const put = (e, r) => { const a = sim.rowDi[r]; a.splice(lowerBound(a, e.di), 0, e.di); sim.row.set(e.id, r); };
    for (let moved = true; moved;) {
      moved = false;
      for (const e of sim.order) {
        const cur = sim.row.get(e.id);
        if (cur === undefined || cur === 0) continue;
        for (let r = 0; r < cur; r++) if (free(r, e.di)) { const a = sim.rowDi[cur]; a.splice(lowerBound(a, e.di), 1); put(e, r); moved = true; break; }
      }
    }
    for (const e of sim.order) {
      if (sim.row.has(e.id)) continue;
      for (let r = 0; r < sim.rowDi.length; r++) if (free(r, e.di)) { put(e, r); break; }
    }
    sim.layouts.push(new Map(sim.row));
  }

  // id -> row for the events shown full size; `need` is a card width in days
  function place(events, rows, need) {
    const sim = simulation(events, rows);
    let s = Math.max(0, Math.floor(Math.log(NEED0 / need) / Math.log(STEP)));
    while (s > 0 && NEED0 / STEP ** s < need) s--;
    while (sim.layouts.length <= s) step(sim, NEED0 / STEP ** sim.layouts.length);
    return sim.layouts[s];
  }

  // the full-size card closest to a day, or null when none is shown
  function nearestShown(events, shown, di) {
    let best = null;
    for (const e of events) if (shown.has(e.id) && (!best || Math.abs(e.di - di) < Math.abs(best.di - di))) best = e;
    return best;
  }

  // the next full-size card after `from` in date order (dir 1) or before it (dir -1), or null
  function stepShown(events, shown, from, dir) {
    let best = null;
    for (const e of events) {
      if (!shown.has(e.id) || (e.di - from.di) * dir <= 0) continue;
      if (!best || Math.abs(e.di - from.di) < Math.abs(best.di - from.di)) best = e;
    }
    return best;
  }

  // zoom (px per day) and centre day for clicking a bubble over a run of faded cards from day a to b: fit the run on
  // screen, but always zoom in at least 2x, since a run can chain wider than the screen
  function clusterZoom(a, b, p, width, zmax) {
    const fit = (width - 300) / Math.max(b - a, 1 / 24);
    return { p: Math.min(zmax, Math.max(fit, p * 2)), center: (a + b) / 2 };
  }

  const api = { prepare, place, nearestShown, stepShown, clusterZoom, ROWS: 2 };
  if (typeof module === 'object' && module.exports) module.exports = api; else root.Placement = api;
})(this);
